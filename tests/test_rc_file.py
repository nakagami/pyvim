import os
import tempfile
from pyvim.rc_file import run_rc_file


def test_run_rc_file_sets_configuration(editor):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            """
def configure(editor):
    editor.show_line_numbers = True
    editor.enable_mouse_support = True
"""
        )
        temp_path = f.name

    try:
        run_rc_file(editor, temp_path)
        assert editor.show_line_numbers is True
        assert editor.enable_mouse_support is True
    finally:
        os.remove(temp_path)


def test_run_rc_file_nonexistent(editor, monkeypatch):
    monkeypatch.setattr("pyvim.rc_file._press_enter_to_continue", lambda: None)
    # Should not raise exception
    run_rc_file(editor, "/nonexistent/path/to/pyvimrc")
