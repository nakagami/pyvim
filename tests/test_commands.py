from pyvim.commands.handler import handle_command


def setup_buffer(editor_buffer, text):
    editor = editor_buffer.editor
    editor.window_arrangement._add_editor_buffer(editor_buffer)
    editor_buffer.buffer.text = text
    editor.sync_with_prompt_toolkit()


def test_go_to_line(editor, editor_buffer):
    setup_buffer(editor_buffer, "line 1\nline 2\nline 3\nline 4\n")
    handle_command(editor, ":3")
    assert editor_buffer.buffer.document.cursor_position_row == 2


def test_delete_command_range(editor, editor_buffer):
    setup_buffer(editor_buffer, "line 1\nline 2\nline 3\nline 4\n")
    handle_command(editor, ":2,3d")
    assert editor_buffer.buffer.text == "line 1\nline 4\n"


def test_copy_command(editor, editor_buffer):
    setup_buffer(editor_buffer, "line 1\nline 2\nline 3\n")
    handle_command(editor, ":1,2co3")
    assert editor_buffer.buffer.text == "line 1\nline 2\nline 3\nline 1\nline 2\n"


def test_yank_command(editor, editor_buffer):
    setup_buffer(editor_buffer, "line 1\nline 2\nline 3\n")
    handle_command(editor, ":1,2ya")
    assert editor.application.clipboard.get_data().text == "line 1\nline 2"


def test_unknown_command(editor, editor_buffer):
    setup_buffer(editor_buffer, "sample text")
    handle_command(editor, ":unknowncmd123")
    # Buffer text is unchanged
    assert editor_buffer.buffer.text == "sample text"
