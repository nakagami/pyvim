import os
import re
from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition, has_focus, vi_insert_mode, vi_navigation_mode
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit import document

from .commands.commands import write_and_quit, quit


__all__ = (
    'create_key_bindings',
)


def _document_find(
    self,
    sub: str,
    in_current_line: bool = False,
    include_current_position: bool = False,
    ignore_case: bool = False,
    count: int = 1,
) -> int | None:
    """
    Find `text` after the cursor, return position relative to the cursor
    position. Return `None` if nothing was found.

    :param count: Find the n-th occurrence.
    """
    assert isinstance(ignore_case, bool)

    if in_current_line:
        text = self.current_line_after_cursor
    else:
        text = self.text_after_cursor

    if not include_current_position:
        if len(text) == 0:
            return None  # (Otherwise, we always get a match for the empty string.)
        else:
            text = text[1:]

    offset = len(self.text) - len(text)

    flags = re.MULTILINE
    if ignore_case:
        flags |= re.IGNORECASE

    try:
        match_all_set = set([(a.start() - offset, a.end() - offset) for a in re.finditer(sub, self.text, flags)])
    except re.error:
        match_all_set = set([(a.start() - offset, a.end() - offset) for a in re.finditer(re.escape(sub), self.text, flags)])

    try:
        match_partial = [(a.start(), a.end()) for a in re.finditer(sub, text, flags)]
    except re.error:
        match_partial = [(a.start(), a.end()) for a in re.finditer(re.escape(sub), text, flags)]

    try:
        for i, match in enumerate([m for m in match_partial if m in match_all_set]):
            if i + 1 == count:
                if include_current_position:
                    return match[0]
                else:
                    return match[0] + 1
    except StopIteration:
        pass
    return None


def _document_find_all(self, sub: str, ignore_case: bool = False) -> list[int]:
    """
    Find all occurrences of the substring. Return a list of absolute
    positions in the document.
    """
    flags = re.MULTILINE
    if ignore_case:
        flags |= re.IGNORECASE
    try:
        return [a.start() for a in re.finditer(sub, self.text, flags)]
    except re.error:
        return [a.start() for a in re.finditer(re.escape(sub), self.text, flags)]


def _document_find_backwards(
    self,
    sub: str,
    in_current_line: bool = False,
    ignore_case: bool = False,
    count: int = 1,
) -> int | None:
    """
    Find `text` before the cursor, return position relative to the cursor
    position. Return `None` if nothing was found.

    :param count: Find the n-th occurrence.
    """
    if in_current_line:
        text = self.current_line_before_cursor
    else:
        text = self.text_before_cursor

    flags = re.MULTILINE
    if ignore_case:
        flags |= re.IGNORECASE
    try:
        iterator = re.finditer(sub, text, flags)
    except re.error:
        iterator = re.finditer(re.escape(sub), text, flags)
    matches = list(reversed(list(iterator)))
    if len(matches) < count:
        return None

    return matches[count - 1].start(0) - len(text)


document.Document.find = _document_find
document.Document.find_all = _document_find_all
document.Document.find_backwards = _document_find_backwards


def create_key_bindings(editor):
    """
    Create custom key bindings.

    This starts with the key bindings, defined by `prompt-toolkit`, but adds
    the ones which are specific for the editor.
    """
    kb = KeyBindings()

    # Filters.
    @Condition
    def vi_buffer_focussed():
        app = get_app()
        if app.layout.has_focus(editor.search_buffer) or app.layout.has_focus(editor.command_buffer):
            return False
        return True

    in_insert_mode = vi_insert_mode & vi_buffer_focussed
    in_navigation_mode = vi_navigation_mode & vi_buffer_focussed

    @kb.add('Z', 'Z', filter=in_navigation_mode)
    def _(event):
        """
        Write and quit.
        """
        write_and_quit(editor, None)
        editor.sync_with_prompt_toolkit()

    @kb.add('Z', 'Q', filter=in_navigation_mode)
    def _(event):
        """
        Quit and discard changes.
        """
        quit(editor, force=True)
        editor.sync_with_prompt_toolkit()

    @kb.add('c-z', filter=in_navigation_mode)
    def _(event):
        """
        Suspend process to background.
        """
        event.app.suspend_to_background()

    @kb.add('c-t')
    def _(event):
        """
        Override default behaviour of prompt-toolkit.
        (Control-T will swap the last two characters before the cursor, because
        that's what readline does.)
        """
        pass

    @kb.add('c-t', filter=in_insert_mode)
    def indent_line(event):
        """
        Indent current line.
        """
        b = event.app.current_buffer

        # Move to start of line.
        pos = b.document.get_start_of_line_position(after_whitespace=True)
        b.cursor_position += pos

        # Insert tab.
        if editor.expand_tab:
            b.insert_text('    ')
        else:
            b.insert_text('\t')

        # Restore cursor.
        b.cursor_position -= pos

    @kb.add('c-d', filter=in_insert_mode)
    def dedent_line(event):
        buffer = event.current_buffer
        document = buffer.document
        a = document.cursor_position + document.get_start_of_line_position()
        b = document.cursor_position + document.get_end_of_line_position()
        text = document.text[a:b]
        space_len = len(text) - len(text.lstrip(' '))
        if space_len:
            if space_len % 4:
                remove_len = space_len % 4
            else:
                remove_len = 4
            text = text[remove_len:]
            buffer.text = document.text[:a] + text + document.text[b:]
            buffer.cursor_position -= remove_len

    @kb.add('c-r', filter=in_navigation_mode, save_before=(lambda e: False))
    def redo(event):
        """
        Redo.
        """
        event.app.current_buffer.redo()

    @kb.add(':', filter=in_navigation_mode)
    def enter_command_mode(event):
        """
        Entering command mode.
        """
        editor.enter_command_mode()

    @kb.add('tab', filter=vi_insert_mode & ~has_focus(editor.command_buffer) & whitespace_before_cursor_on_line)
    def autocomplete_or_indent(event):
        """
        When the 'tab' key is pressed with only whitespace character before the
        cursor, do autocompletion. Otherwise, insert indentation.
        """
        b = event.app.current_buffer
        if editor.expand_tab:
            b.insert_text('    ')
        else:
            b.insert_text('\t')

    @kb.add('escape', filter=has_focus(editor.command_buffer))
    @kb.add('c-c', filter=has_focus(editor.command_buffer))
    @kb.add('backspace', filter=has_focus(editor.command_buffer) & Condition(lambda: editor.command_buffer.text == ''))
    def leave_command_mode(event):
        """
        Leaving command mode.
        """
        editor.leave_command_mode()

    @kb.add('c-w', 'c-w', filter=in_navigation_mode)
    def focus_next_window(event):
        editor.window_arrangement.cycle_focus()
        editor.sync_with_prompt_toolkit()

    @kb.add('c-w', 'n', filter=in_navigation_mode)
    def horizontal_split(event):
        """
        Split horizontally.
        """
        editor.window_arrangement.hsplit(None)
        editor.sync_with_prompt_toolkit()

    @kb.add('c-w', 'v', filter=in_navigation_mode)
    def vertical_split(event):
        """
        Split vertically.
        """
        editor.window_arrangement.vsplit(None)
        editor.sync_with_prompt_toolkit()

    @kb.add('g', 't', filter=in_navigation_mode)
    def focus_next_tab(event):
        editor.window_arrangement.go_to_next_tab()
        editor.sync_with_prompt_toolkit()

    @kb.add('g', 'T', filter=in_navigation_mode)
    def focus_previous_tab(event):
        editor.window_arrangement.go_to_previous_tab()
        editor.sync_with_prompt_toolkit()

    @kb.add('f1')
    def show_help(event):
        editor.show_help()

    @Condition
    def in_file_explorer_mode():
        return bool(editor.current_editor_buffer and editor.current_editor_buffer.in_file_explorer_mode)

    @kb.add('enter', filter=in_file_explorer_mode)
    def open_path(event):
        """
        Open file/directory in file explorer mode.
        """
        name_under_cursor = event.current_buffer.document.current_line
        new_path = os.path.normpath(os.path.join(
            editor.current_editor_buffer.location, name_under_cursor))

        editor.window_arrangement.open_buffer(
            new_path, show_in_current_window=True)
        editor.sync_with_prompt_toolkit()

    @kb.add('-', filter=in_file_explorer_mode)
    def to_parent_directory(event):
        new_path = os.path.normpath(os.path.join(
            editor.current_editor_buffer.location, '..'))

        editor.window_arrangement.open_buffer(
            new_path, show_in_current_window=True)
        editor.sync_with_prompt_toolkit()

    @kb.add("G", filter=vi_navigation_mode)
    def to_nth_line(event):
        # I don't know why, but the default behaviour of the prompt toolkit is that <number>G does not work well.
        # With this implementation, 1G same as G and moves to the end of the line.
        # I don't know how to fix it, so please use gg instead of 1G when moving to the first line
        buf = event.current_buffer
        count = (buf.document.line_count if event.arg == 1 else event.arg - 1) - buf.document.cursor_position_row
        if count > 0:
            buf.auto_down(count=count, go_to_start_of_line_if_history_changes=True)
        elif count < 0:
            buf.auto_up(count=-count, go_to_start_of_line_if_history_changes=True)

    return kb


@Condition
def whitespace_before_cursor_on_line():
    """
    Filter which evaluates to True when the characters before the cursor are
    whitespace, or we are at the start of te line.
    """
    b = get_app().current_buffer
    before_cursor = b.document.current_line_before_cursor

    return bool(not before_cursor or before_cursor[-1].isspace())
