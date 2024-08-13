import os
from prompt_toolkit.application import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.vi_state import InputMode
from prompt_toolkit.key_binding.bindings import vi
from prompt_toolkit.key_binding.bindings.vi import (
    create_text_object_decorator, TextObjectType, TextObject,
    Callable, _OF, Filter, Always, Keys, vi_waiting_for_text_object_mode,
)
from prompt_toolkit.key_binding.key_processor import KeyPressEvent as E
from prompt_toolkit.clipboard import ClipboardData
from prompt_toolkit.filters import (
    Condition, has_focus, vi_insert_mode, vi_navigation_mode, is_read_only
)
from prompt_toolkit.filters.app import in_paste_mode, vi_selection_mode, vi_replace_single_mode
from prompt_toolkit.selection import SelectionType

from .document import Document
from .commands.commands import write_and_quit, quit


__all__ = (
    'create_key_bindings',
)


def _create_operator_decorator(
    key_bindings: KeyBindings,
) -> Callable[..., Callable[[_OF], _OF]]:
    """
    Create a decorator that can be used for registering Vi operators.
    """

    def operator_decorator(
        *keys: Keys | str, filter: Filter = Always(), eager: bool = False
    ) -> Callable[[_OF], _OF]:
        """
        Register a Vi operator.

        Usage::

            @operator('d', filter=...)
            def handler(event, text_object):
                # Do something with the text object here.
        """

        def decorator(operator_func: _OF) -> _OF:
            @key_bindings.add(
                *keys,
                filter=~vi_waiting_for_text_object_mode & filter & vi_navigation_mode,
                eager=eager,
            )
            def _operator_in_navigation(event: E) -> None:
                """
                Handle operator in navigation mode.
                """
                # When this key binding is matched, only set the operator
                # function in the ViState. We should execute it after a text
                # object has been received.
                event.app.key_processor._editor.start_edit_command(event)
                event.app.vi_state.operator_func = operator_func
                event.app.vi_state.operator_arg = event.arg

            @key_bindings.add(
                *keys,
                filter=~vi_waiting_for_text_object_mode & filter & vi_selection_mode,
                eager=eager,
            )
            def _operator_in_selection(event: E) -> None:
                """
                Handle operator in selection mode.
                """
                buff = event.current_buffer
                selection_state = buff.selection_state

                if selection_state is not None:
                    # Create text object from selection.
                    if selection_state.type == SelectionType.LINES:
                        text_obj_type = TextObjectType.LINEWISE
                    elif selection_state.type == SelectionType.BLOCK:
                        text_obj_type = TextObjectType.BLOCK
                    else:
                        text_obj_type = TextObjectType.INCLUSIVE

                    text_object = TextObject(
                        selection_state.original_cursor_position - buff.cursor_position,
                        type=text_obj_type,
                    )

                    # Execute operator.
                    operator_func(event, text_object)

                    # Quit selection mode.
                    buff.selection_state = None

            return operator_func

        return decorator

    return operator_decorator


vi.create_operator_decorator = _create_operator_decorator


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
        editor.finish_edit_command(event)

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
        editor.start_edit_command()
        event.app.vi_state.input_mode = InputMode.INSERT

    @kb.add("insert", filter=vi_insert_mode)
    def _navigation_mode(event: E) -> None:
        """
        Pressing the Insert key.
        """
        editor.finish_edit_command(event)
        event.app.vi_state.input_mode = InputMode.NAVIGATION

    @kb.add("a", filter=vi_navigation_mode & ~is_read_only)
    # ~IsReadOnly, because we want to stay in navigation mode for
    # read-only buffers.
    def _a(event: E) -> None:
        editor.start_edit_command()

        event.current_buffer.cursor_position += (
            event.current_buffer.document.get_cursor_right_position()
        )
        event.app.vi_state.input_mode = InputMode.INSERT

    @kb.add("A", filter=vi_navigation_mode & ~is_read_only)
    def _A(event: E) -> None:
        editor.start_edit_command()

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
        editor.start_edit_command(event)

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
        editor.start_edit_command(event)

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
        editor.start_edit_command()

        buffer = event.current_buffer
        deleted = buffer.delete(count=buffer.document.get_end_of_line_position())
        event.app.clipboard.set_text(deleted)

        editor.finish_edit_command()

    @kb.add("d", "d", filter=vi_navigation_mode)
    def _delete_line(event: E) -> None:
        """
        Delete line. (Or the following 'n' lines.)
        """
        editor.start_edit_command(event)

        buffer = event.current_buffer

        # Split string in before/deleted/after text.
        lines = buffer.document.lines

        before = "\n".join(lines[: buffer.document.cursor_position_row])
        deleted = "\n".join(
            lines[
                buffer.document.cursor_position_row: buffer.document.cursor_position_row + event.arg
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

        editor.finish_edit_command()

    @kb.add("i", filter=vi_navigation_mode & ~is_read_only)
    def _i(event: E) -> None:
        editor.start_edit_command()

        event.app.vi_state.input_mode = InputMode.INSERT

    @kb.add("I", filter=vi_navigation_mode & ~is_read_only)
    def _I(event: E) -> None:
        editor.start_edit_command()

        event.app.vi_state.input_mode = InputMode.INSERT
        event.current_buffer.cursor_position += (
            event.current_buffer.document.get_start_of_line_position(
                after_whitespace=True
            )
        )

    @kb.add("J", filter=vi_navigation_mode & ~is_read_only)
    def _join(event: E) -> None:
        """
        Join lines.
        """
        editor.start_edit_command()

        for i in range(event.arg):
            event.current_buffer.join_next_line()

        editor.finish_edit_command()

    @kb.add("g", "J", filter=vi_navigation_mode & ~is_read_only)
    def _join_nospace(event: E) -> None:
        """
        Join lines without space.
        """
        editor.start_edit_command()

        for i in range(event.arg):
            event.current_buffer.join_next_line(separator="")

        editor.finish_edit_command()

    @kb.add("r", filter=vi_navigation_mode)
    def _replace(event: E) -> None:
        """
        Go to 'replace-single'-mode.
        """
        editor.start_edit_command()

        event.app.vi_state.input_mode = InputMode.REPLACE_SINGLE

    @kb.add("R", filter=vi_navigation_mode)
    def _replace_mode(event: E) -> None:
        """
        Go to 'replace'-mode.
        """
        editor.start_edit_command()

        event.app.vi_state.input_mode = InputMode.REPLACE

    @kb.add("s", filter=vi_navigation_mode & ~is_read_only)
    def _substitute(event: E) -> None:
        """
        Substitute with new text
        (Delete character(s) and go to insert mode.)
        """
        editor.start_edit_command()

        text = event.current_buffer.delete(count=event.arg)
        event.app.clipboard.set_text(text)
        event.app.vi_state.input_mode = InputMode.INSERT

    @kb.add("x", filter=vi_navigation_mode)
    def _delete(event: E) -> None:
        """
        Delete character.
        """
        editor.start_edit_command()

        buff = event.current_buffer
        count = min(event.arg, len(buff.document.current_line_after_cursor))
        if count:
            text = event.current_buffer.delete(count=count)
            event.app.clipboard.set_text(text)

    @kb.add("X", filter=vi_navigation_mode)
    def _delete_before_cursor(event: E) -> None:
        editor.start_edit_command()

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
        cursor_position = buffer.cursor_position
        a = document.cursor_position + document.get_start_of_line_position()
        b = document.cursor_position + document.get_end_of_line_position()
        text = document.text[a:b]
        if buffer.expand_tab:
            space_len = len(text) - len(text.lstrip(' '))
            if space_len:
                if space_len % buffer.shiftwidth:
                    remove_len = space_len % buffer.shiftwidth
                else:
                    remove_len = buffer.shiftwidth
                text = text[remove_len:]
                buffer.text = document.text[:a] + text + document.text[b:]
                buffer.cursor_position = cursor_position - remove_len
        else:
            for i in range(a, b):
                if document.text[i] == '\t':
                    buffer.text = document.text[:i] + document.text[i + 1:]
                    buffer.cursor_position = cursor_position - 1
                    break

    @kb.add("O", filter=vi_navigation_mode & ~is_read_only)
    def _open_above(event: E) -> None:
        """
        Open line above and enter insertion mode
        """
        editor.start_edit_command()

        event.current_buffer.insert_line_above(copy_margin=not in_paste_mode())
        event.app.vi_state.input_mode = InputMode.INSERT

    @kb.add("o", filter=vi_navigation_mode & ~is_read_only)
    def _open_below(event: E) -> None:
        """
        Open line below and enter insertion mode
        """
        editor.start_edit_command()

        event.current_buffer.insert_line_below(copy_margin=not in_paste_mode())
        event.app.vi_state.input_mode = InputMode.INSERT

    @kb.add("~", filter=vi_navigation_mode)
    def _reverse_case(event: E) -> None:
        """
        Reverse case of current character and move cursor forward.
        """
        editor.start_edit_command()

        buffer = event.current_buffer
        c = buffer.document.current_char

        if c is not None and c != "\n":
            buffer.insert_text(c.swapcase(), overwrite=True)

        editor.finish_edit_command()

    @kb.add("g", "u", "u", filter=vi_navigation_mode & ~is_read_only)
    def _lowercase_line(event: E) -> None:
        """
        Lowercase current line.
        """
        editor.start_edit_command()

        buff = event.current_buffer
        buff.transform_current_line(lambda s: s.lower())

        editor.finish_edit_command()

    @kb.add("g", "U", "U", filter=vi_navigation_mode & ~is_read_only)
    def _uppercase_line(event: E) -> None:
        """
        Uppercase current line.
        """
        editor.start_edit_command()

        buff = event.current_buffer
        buff.transform_current_line(lambda s: s.upper())

        editor.finish_edit_command()

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
        if b.expand_tab:
            b.insert_text(' ' * b.shiftwidth)
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
        if b.expand_tab:
            b.insert_text(' ' * b.tabstop)
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
        buf = event.current_buffer
        count = number - buf.document.cursor_position_row - 1
        if count > 0:
            buf.auto_down(count=count, go_to_start_of_line_if_history_changes=True)
        elif count < 0:
            buf.auto_up(count=-count, go_to_start_of_line_if_history_changes=True)

    @kb.add("G", filter=vi_navigation_mode)
    def to_nth_line(event):
        if event._arg is None:
            # G without line number, move to last line
            _nth_line(event, event.current_buffer.document.line_count)
        else:
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

    @kb.add(".", filter=vi_navigation_mode)
    def dot(event):
        editor.replay_edit_command()

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

    @kb.add(Keys.Any, filter=vi_replace_single_mode)
    def _replace_single(event: E) -> None:
        """
        Replace single character at cursor position.
        """
        editor.append_edit_command(event.key_sequence[0])

        event.current_buffer.insert_text(event.data, overwrite=True)
        event.current_buffer.cursor_position -= 1
        event.app.vi_state.input_mode = InputMode.NAVIGATION

        editor.finish_edit_command()

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
            end = document.find_next_word_beginning(count=event.arg) or document.get_end_of_document_position()
            eol = document.text_after_cursor[:end].find('\n')
            if eol != -1:
                end = eol
        else:
            end = document.find_next_word_ending(include_current_position=True, count=event.arg)
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
