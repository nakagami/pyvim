from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.search import SearchDirection, SearchState
from prompt_toolkit.document import Document

from pyvim.completion import DocumentCompleter
from pyvim.reporting import report

import stat
import os
import weakref

__all__ = (
    'EditorBuffer',
)


def _search(
    self,
    search_state: SearchState,
    include_current_position: bool = False,
    count: int = 1,
) -> tuple[int, int] | None:
    """
    Execute search. Return (working_index, cursor_position) tuple when this
    search is applied. Returns `None` when this text cannot be found.
    """
    assert count > 0

    text = search_state.text
    direction = search_state.direction
    ignore_case = search_state.ignore_case()

    def search_once(
        working_index: int, document: Document
    ) -> tuple[int, Document] | None:
        """
        Do search one time.
        Return (working_index, document) or `None`
        """
        if direction == SearchDirection.FORWARD:
            # Try find at the current input.
            new_index = document.find(
                text,
                include_current_position=include_current_position,
                ignore_case=ignore_case,
            )

            if new_index is not None:
                return (
                    working_index,
                    Document(document.text, document.cursor_position + new_index),
                )
            elif self._editor.enable_wrapscan:
                # No match, go forward in the history. (Include len+1 to wrap around.)
                # (Here we should always include all cursor positions, because
                # it's a different line.)
                for i in range(working_index + 1, len(self._working_lines) + 1):
                    i %= len(self._working_lines)

                    document = Document(self._working_lines[i], 0)
                    new_index = document.find(
                        text, include_current_position=True, ignore_case=ignore_case
                    )
                    if new_index is not None:
                        return (i, Document(document.text, new_index))
        else:
            # Try find at the current input.
            new_index = document.find_backwards(text, ignore_case=ignore_case)

            if new_index is not None:
                return (
                    working_index,
                    Document(document.text, document.cursor_position + new_index),
                )
            elif self._editor.enable_wrapscan:
                # No match, go back in the history. (Include -1 to wrap around.)
                for i in range(working_index - 1, -2, -1):
                    i %= len(self._working_lines)

                    document = Document(
                        self._working_lines[i], len(self._working_lines[i])
                    )
                    new_index = document.find_backwards(
                        text, ignore_case=ignore_case
                    )
                    if new_index is not None:
                        return (
                            i,
                            Document(document.text, len(document.text) + new_index),
                        )
        return None

    # Do 'count' search iterations.
    working_index = self.working_index
    document = self.document
    for _ in range(count):
        result = search_once(working_index, document)
        if result is None:
            return None  # Nothing found.
        else:
            working_index, document = result

    return (working_index, document.cursor_position)


Buffer._search = _search


class EditorBuffer(object):
    """
    Wrapper around a `prompt-toolkit` buffer.

    A 'prompt-toolkit' `Buffer` doesn't know anything about files, changes,
    etc... This wrapper contains the necessary data for the editor.
    """
    def __init__(self, editor, location=None, text=None):
        assert location is None or isinstance(location, str)
        assert text is None or isinstance(text, str)
        assert not (location and text)

        self._editor_ref = weakref.ref(editor)
        self.location = location
        self.encoding = 'utf-8'

        #: is_new: True when this file does not yet exist in the storage.
        self.is_new = True

        # Empty if not in file explorer mode, directory path otherwise.
        self.isdir = False

        # Read text.
        if location:
            text = self._read(location)
        else:
            text = text or ''

        self._file_content = text

        # Create Buffer.
        self.buffer = Buffer(
            multiline=True,
            completer=DocumentCompleter(editor, self),
            document=Document(text, 0),
            on_text_changed=lambda _: self.run_reporter())
        self.buffer._editor = editor

        # List of reporting errors.
        self.report_errors = []
        self._reporter_is_running = False

    @property
    def editor(self):
        """ Back reference to the Editor. """
        return self._editor_ref()

    @property
    def has_unsaved_changes(self):
        """
        True when some changes are not yet written to file.
        """
        return self._file_content != self.buffer.text

    @property
    def in_file_explorer_mode(self):
        """
        True when we are in file explorer mode (when this is a directory).
        """
        return self.isdir

    def _read(self, location):
        """
        Read file I/O backend.
        """
        for io in self.editor.io_backends:
            if io.can_open_location(location):
                # Found an I/O backend.
                exists = io.exists(location)
                self.isdir = io.isdir(location)

                if exists in (True, NotImplemented):
                    # File could exist. Read it.
                    self.is_new = False
                    try:
                        text, self.encoding = io.read(location)

                        # Replace \r\n by \n.
                        text = text.replace('\r\n', '\n')

                        # Drop trailing newline while editing.
                        # (prompt-toolkit doesn't enforce the trailing newline.)
                        if text.endswith('\n'):
                            text = text[:-1]
                    except Exception as e:
                        self.editor.show_message('Cannot read %r: %r' % (location, e))
                        return ''
                    else:
                        return text
                else:
                    # File doesn't exist.
                    self.is_new = True
                    return ''

        self.editor.show_message('Cannot read: %r' % location)
        return ''

    def reload(self):
        """
        Reload file again from storage.
        """
        text = self._read(self.location)
        cursor_position = min(self.buffer.cursor_position, len(text))

        self.buffer.document = Document(text, cursor_position)
        self._file_content = text

    def write(self, location=None, force=False):
        """
        Write file to I/O backend.
        """
        # Take location and expand tilde.
        if location is not None:
            self.location = location
        assert self.location

        # Find I/O backend that handles this location.
        for io in self.editor.io_backends:
            if io.can_open_location(self.location):
                break
        else:
            self.editor.show_message('Unknown location: %r' % location)

        # Write it.
        toggle_write_permission = False
        done = False
        while (not done):
            try:
                io.write(self.location, self.buffer.text + '\n', self.encoding)
                self.is_new = False
                if toggle_write_permission:
                    try:
                        os.chmod(self.location, os.stat(self.location).st_mode & ~stat.S_IWRITE)
                        done = True
                    except Exception as e:
                        self.editor.show_message('%s' % e)
                        done = True
            except Exception as e:
                if os.path.isfile(self.location) and (not os.access(self.location, os.W_OK)):  # File is not writable
                    if force:
                        if not toggle_write_permission:
                            try:
                                os.chmod(self.location, os.stat(self.location).st_mode | stat.S_IWRITE)
                                toggle_write_permission = True
                            except Exception as e:
                                self.editor.show_message('%s' % e)
                                done = True
                        else:
                            # E.g. "No such file or directory."
                            self.editor.show_message('%s' % e)
                            done = True
                    else:
                        self.editor.show_message("'readonly' option is set (add ! to override)")
                        done = True
            else:
                # When the save succeeds: update: _file_content.
                self._file_content = self.buffer.text
                done = True

    def get_display_name(self, short=False):
        """
        Return name as displayed.
        """
        if self.location is None:
            return '[New file]'
        elif short:
            return os.path.basename(self.location)
        else:
            return self.location

    def __repr__(self):
        return '%s(buffer=%r)' % (self.__class__.__name__, self.buffer)

    def run_reporter(self):
        " Buffer text changed. "
        if not self._reporter_is_running:
            # Don't run reporter when we don't have a location. (We need to
            # know the filetype, actually.)
            if self.location is None:
                return

            self._reporter_is_running = True
            self.report_errors = report(self.location, self.buffer.document)
            get_app().invalidate()
            self._reporter_is_running = False
