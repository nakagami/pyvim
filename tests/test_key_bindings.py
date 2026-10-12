from prompt_toolkit.application.current import set_app
from prompt_toolkit.key_binding.key_processor import KeyPressEvent, KeyPress
from prompt_toolkit.key_binding.vi_state import InputMode


def setup_test_editor(editor, editor_buffer, text):
    editor.window_arrangement._add_editor_buffer(editor_buffer)
    editor_buffer.buffer.text = text
    editor.sync_with_prompt_toolkit()
    return editor.key_bindings


def test_change_current_line_single(editor, editor_buffer):
    kb = setup_test_editor(editor, editor_buffer, "    hello world\nline 2\n")
    editor_buffer.buffer.cursor_position = 0

    with set_app(editor.application):
        binding = next(b for b in kb.bindings if b.keys == ("c", "c"))
        event = KeyPressEvent(
            key_processor_ref=lambda: editor.key_processor,
            arg=1,
            key_sequence=[KeyPress("c"), KeyPress("c")],
            previous_key_sequence=[],
            is_repeat=False,
        )
        binding.call(event)

    # Indentation preserved, content cleared on line 1, cursor at indent
    assert editor_buffer.buffer.text == "    \nline 2\n"
    assert editor_buffer.buffer.cursor_position == 4
    assert editor.application.vi_state.input_mode == InputMode.INSERT
    assert editor.application.clipboard.get_data().text == "    hello world"


def test_change_current_line_with_count(editor, editor_buffer):
    kb = setup_test_editor(editor, editor_buffer, "  first line\n  second line\nthird line\n")
    editor_buffer.buffer.cursor_position = 0

    with set_app(editor.application):
        binding = next(b for b in kb.bindings if b.keys == ("c", "c"))
        event = KeyPressEvent(
            key_processor_ref=lambda: editor.key_processor,
            arg=2,
            key_sequence=[KeyPress("c"), KeyPress("c")],
            previous_key_sequence=[],
            is_repeat=False,
        )
        binding.call(event)

    # First 2 lines replaced with single indented line
    assert editor_buffer.buffer.text == "  \nthird line\n"
    assert editor_buffer.buffer.cursor_position == 2
    assert editor.application.vi_state.input_mode == InputMode.INSERT
    assert editor.application.clipboard.get_data().text == "  first line\n  second line"
