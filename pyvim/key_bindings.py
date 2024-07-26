import os
import re
from prompt_toolkit.application import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.vi_state import InputMode
from prompt_toolkit.key_binding.bindings.vi import (
    create_text_object_decorator, in_block_selection, TextObject
)
from prompt_toolkit.key_binding.key_processor import KeyPressEvent as E
from prompt_toolkit.clipboard import ClipboardData
from prompt_toolkit.document import Document
from prompt_toolkit.filters import (
    Condition, has_focus, vi_insert_mode, vi_navigation_mode, is_read_only
)
from prompt_toolkit.filters.app import in_paste_mode, vi_selection_mode
from prompt_toolkit.selection import SelectionType

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
        iterator = re.finditer(sub, self.text, flags)
    except re.error:
        iterator = re.finditer(re.escape(sub), text, flags)

    try:
        for i, match in enumerate([m for m in iterator if m.start() >= offset]):
            if i + 1 == count:
                if include_current_position:
                    return match.start() - offset
                else:
                    return match.start() - offset + 1
    except StopIteration:
        pass
    return None


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


Document.find = _document_find
Document.find_backwards = _document_find_backwards


def create_key_bindings(editor):
    """
    Create custom key bindings.

    This starts with the key bindings, defined by `prompt-toolkit`, but adds
    the ones which are specific for the editor.
    """
    kb = KeyBindings()

    text_object = create_text_object_decorator(kb)

    # Filters.
    @Condition
    def vi_buffer_focussed():
        app = get_app()
        if app.layout.has_focus(editor.search_buffer) or app.layout.has_focus(editor.command_buffer):
            return False
        return True

    in_insert_mode = vi_insert_mode & vi_buffer_focussed
    in_navigation_mode = vi_navigation_mode & vi_buffer_focussed

    @kb.add("escape")
    def _back_to_navigation(event: E) -> None:
        """
        Escape goes to vi navigation mode.
        """
        buffer = event.current_buffer
        vi_state = event.app.vi_state

        if vi_state.input_mode in (InputMode.INSERT, InputMode.REPLACE):
            buffer.cursor_position += buffer.document.get_cursor_left_position()

        vi_state.input_mode = InputMode.NAVIGATION

        if bool(buffer.selection_state):
            buffer.exit_selection()

    # ** In navigation mode **

    @kb.add("insert", filter=vi_navigation_mode)
    def _insert_mode(event: E) -> None:
        """
        Pressing the Insert key.
        """
        event.app.vi_state.input_mode = InputMode.INSERT

    @kb.add("insert", filter=vi_insert_mode)
    def _navigation_mode(event: E) -> None:
        """
        Pressing the Insert key.
        """
        event.app.vi_state.input_mode = InputMode.NAVIGATION

    @kb.add("a", filter=vi_navigation_mode & ~is_read_only)
    # ~IsReadOnly, because we want to stay in navigation mode for
    # read-only buffers.
    def _a(event: E) -> None:
        event.current_buffer.cursor_position += (
            event.current_buffer.document.get_cursor_right_position()
        )
        event.app.vi_state.input_mode = InputMode.INSERT

    @kb.add("A", filter=vi_navigation_mode & ~is_read_only)
    def _A(event: E) -> None:
        event.current_buffer.cursor_position += (
            event.current_buffer.document.get_end_of_line_position()
        )
        event.app.vi_state.input_mode = InputMode.INSERT

    @kb.add("C", filter=vi_navigation_mode & ~is_read_only)
    def _change_until_end_of_line(event: E) -> None:
        """
        Change to end of line.
        Same as 'c$' (which is implemented elsewhere.)
        """
        buffer = event.current_buffer

        deleted = buffer.delete(count=buffer.document.get_end_of_line_position())
        event.app.clipboard.set_text(deleted)
        event.app.vi_state.input_mode = InputMode.INSERT

    @kb.add("c", "c", filter=vi_navigation_mode & ~is_read_only)
    @kb.add("S", filter=vi_navigation_mode & ~is_read_only)
    def _change_current_line(event: E) -> None:  # TODO: implement 'arg'
        """
        Change current line
        """
        buffer = event.current_buffer

        # We copy the whole line.
        data = ClipboardData(buffer.document.current_line, SelectionType.LINES)
        event.app.clipboard.set_data(data)

        # But we delete after the whitespace
        buffer.cursor_position += buffer.document.get_start_of_line_position(
            after_whitespace=True
        )
        buffer.delete(count=buffer.document.get_end_of_line_position())
        event.app.vi_state.input_mode = InputMode.INSERT

    @kb.add("D", filter=vi_navigation_mode)
    def _delete_until_end_of_line(event: E) -> None:
        """
        Delete from cursor position until the end of the line.
        """
        buffer = event.current_buffer
        deleted = buffer.delete(count=buffer.document.get_end_of_line_position())
        event.app.clipboard.set_text(deleted)

    @kb.add("d", "d", filter=vi_navigation_mode)
    def _delete_line(event: E) -> None:
        """
        Delete line. (Or the following 'n' lines.)
        """
        buffer = event.current_buffer

        # Split string in before/deleted/after text.
        lines = buffer.document.lines

        before = "\n".join(lines[: buffer.document.cursor_position_row])
        deleted = "\n".join(
            lines[
                buffer.document.cursor_position_row: buffer.document.cursor_position_row
                + event.arg
            ]
        )
        after = "\n".join(lines[buffer.document.cursor_position_row + event.arg:])

        # Set new text.
        if before and after:
            before = before + "\n"

        # Set text and cursor position.
        buffer.document = Document(
            text=before + after,
            # Cursor At the start of the first 'after' line, after the leading whitespace.
            cursor_position=len(before) + len(after) - len(after.lstrip(" ")),
        )

        # Set clipboard data
        event.app.clipboard.set_data(ClipboardData(deleted, SelectionType.LINES))

    @kb.add("x", filter=vi_selection_mode)
    def _cut(event: E) -> None:
        """
        Cut selection.
        ('x' is not an operator.)
        """
        clipboard_data = event.current_buffer.cut_selection()
        event.app.clipboard.set_data(clipboard_data)

    @kb.add("i", filter=vi_navigation_mode & ~is_read_only)
    def _i(event: E) -> None:
        event.app.vi_state.input_mode = InputMode.INSERT

    @kb.add("I", filter=vi_navigation_mode & ~is_read_only)
    def _I(event: E) -> None:
        event.app.vi_state.input_mode = InputMode.INSERT
        event.current_buffer.cursor_position += (
            event.current_buffer.document.get_start_of_line_position(
                after_whitespace=True
            )
        )

    @kb.add("I", filter=in_block_selection & ~is_read_only)
    def insert_in_block_selection(event: E, after: bool = False) -> None:
        """
        Insert in block selection mode.
        """
        buff = event.current_buffer

        # Store all cursor positions.
        positions = []

        if after:

            def get_pos(from_to: tuple[int, int]) -> int:
                return from_to[1]

        else:

            def get_pos(from_to: tuple[int, int]) -> int:
                return from_to[0]

        for i, from_to in enumerate(buff.document.selection_ranges()):
            positions.append(get_pos(from_to))
            if i == 0:
                buff.cursor_position = get_pos(from_to)

        buff.multiple_cursor_positions = positions

        # Go to 'INSERT_MULTIPLE' mode.
        event.app.vi_state.input_mode = InputMode.INSERT_MULTIPLE
        buff.exit_selection()

    @kb.add("A", filter=in_block_selection & ~is_read_only)
    def _append_after_block(event: E) -> None:
        insert_in_block_selection(event, after=True)

    @kb.add("J", filter=vi_navigation_mode & ~is_read_only)
    def _join(event: E) -> None:
        """
        Join lines.
        """
        for i in range(event.arg):
            event.current_buffer.join_next_line()

    @kb.add("g", "J", filter=vi_navigation_mode & ~is_read_only)
    def _join_nospace(event: E) -> None:
        """
        Join lines without space.
        """
        for i in range(event.arg):
            event.current_buffer.join_next_line(separator="")

    @kb.add("J", filter=vi_selection_mode & ~is_read_only)
    def _join_selection(event: E) -> None:
        """
        Join selected lines.
        """
        event.current_buffer.join_selected_lines()

    @kb.add("g", "J", filter=vi_selection_mode & ~is_read_only)
    def _join_selection_nospace(event: E) -> None:
        """
        Join selected lines without space.
        """
        event.current_buffer.join_selected_lines(separator="")

    @kb.add("r", filter=vi_navigation_mode)
    def _replace(event: E) -> None:
        """
        Go to 'replace-single'-mode.
        """
        event.app.vi_state.input_mode = InputMode.REPLACE_SINGLE

    @kb.add("R", filter=vi_navigation_mode)
    def _replace_mode(event: E) -> None:
        """
        Go to 'replace'-mode.
        """
        event.app.vi_state.input_mode = InputMode.REPLACE

    @kb.add("s", filter=vi_navigation_mode & ~is_read_only)
    def _substitute(event: E) -> None:
        """
        Substitute with new text
        (Delete character(s) and go to insert mode.)
        """
        text = event.current_buffer.delete(count=event.arg)
        event.app.clipboard.set_text(text)
        event.app.vi_state.input_mode = InputMode.INSERT

    @kb.add("x", filter=vi_navigation_mode)
    def _delete(event: E) -> None:
        """
        Delete character.
        """
        buff = event.current_buffer
        count = min(event.arg, len(buff.document.current_line_after_cursor))
        if count:
            text = event.current_buffer.delete(count=count)
            event.app.clipboard.set_text(text)

    @kb.add("X", filter=vi_navigation_mode)
    def _delete_before_cursor(event: E) -> None:
        buff = event.current_buffer
        count = min(event.arg, len(buff.document.current_line_before_cursor))
        if count:
            text = event.current_buffer.delete_before_cursor(count=count)
            event.app.clipboard.set_text(text)

    @kb.add(">", ">", filter=vi_navigation_mode)
    @kb.add("c-t", filter=vi_insert_mode)
    def _indent(event: E) -> None:
        """
        Indent lines.
        """
        from prompt_toolkit.buffer import indent
        buffer = event.current_buffer
        current_row = buffer.document.cursor_position_row
        indent(buffer, current_row, current_row + event.arg)

    @kb.add("<", "<", filter=vi_navigation_mode)
    @kb.add('c-d', filter=in_insert_mode)
    def _unindent(event):
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

    @kb.add("O", filter=vi_navigation_mode & ~is_read_only)
    def _open_above(event: E) -> None:
        """
        Open line above and enter insertion mode
        """
        event.current_buffer.insert_line_above(copy_margin=not in_paste_mode())
        event.app.vi_state.input_mode = InputMode.INSERT

    @kb.add("o", filter=vi_navigation_mode & ~is_read_only)
    def _open_below(event: E) -> None:
        """
        Open line below and enter insertion mode
        """
        event.current_buffer.insert_line_below(copy_margin=not in_paste_mode())
        event.app.vi_state.input_mode = InputMode.INSERT

    @kb.add("~", filter=vi_navigation_mode)
    def _reverse_case(event: E) -> None:
        """
        Reverse case of current character and move cursor forward.
        """
        buffer = event.current_buffer
        c = buffer.document.current_char

        if c is not None and c != "\n":
            buffer.insert_text(c.swapcase(), overwrite=True)

    @kb.add("g", "u", "u", filter=vi_navigation_mode & ~is_read_only)
    def _lowercase_line(event: E) -> None:
        """
        Lowercase current line.
        """
        buff = event.current_buffer
        buff.transform_current_line(lambda s: s.lower())

    @kb.add("g", "U", "U", filter=vi_navigation_mode & ~is_read_only)
    def _uppercase_line(event: E) -> None:
        """
        Uppercase current line.
        """
        buff = event.current_buffer
        buff.transform_current_line(lambda s: s.upper())

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

    def _nth_line(event, number):
        # I don't know why, but the default behaviour of the prompt toolkit is that <number>G does not work well.
        # With this implementation, 1G same as G and moves to the end of the line.
        # I don't know how to fix it, so please use gg instead of 1G when moving to the first line
        buf = event.current_buffer
        count = (buf.document.line_count if number == 1 else number - 1) - buf.document.cursor_position_row
        if count > 0:
            buf.auto_down(count=count, go_to_start_of_line_if_history_changes=True)
        elif count < 0:
            buf.auto_up(count=-count, go_to_start_of_line_if_history_changes=True)

    @kb.add("G", filter=vi_navigation_mode)
    def to_nth_line(event):
        _nth_line(event, event.arg)

    for c in "abcdefghijklmnopqrstuvwxyz":
        @kb.add("m", c, filter=vi_navigation_mode)
        def mark(event):
            editor.current_editor_buffer.buffer.mark[event.key_sequence[1].data] = event.current_buffer.document.cursor_position_row + 1

        @kb.add("'", c, filter=vi_navigation_mode)
        def jump(event):
            k = event.key_sequence[1].data
            v = editor.current_editor_buffer.buffer.mark.get(k)
            if v:
                _nth_line(event, v)

    # ** In explorer mode **

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

    #
    # *** Operators ***
    #

    @text_object("w", no_move_handler=True)
    def _word_forward(event: E) -> TextObject:
        """
        'word' forward. 'cw', 'dw': Delete/change one word.
        """
        document = event.current_buffer.document
        if document.current_char in ('\n', ''):
            return None
        if document.current_char.isspace():
            end = document.find_next_word_beginning(count=event.arg)
            eol = document.text_after_cursor[:end].find('\n')
            if eol != -1:
                end = eol
        else:
            end = document.find_next_word_ending(count=event.arg)
        return TextObject(end)

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
