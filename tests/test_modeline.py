"""
Tests for vim modeline parsing (Issue #42).
"""

from pyvim.modeline import _parse_modeline_line, parse_modelines


def test_no_modeline():
    assert _parse_modeline_line("just a comment") is None


def test_simple_vim_no_set():
    opts = _parse_modeline_line("# vim: ft=python:ts=4:sw=2:et")
    assert opts == {"ft": "python", "ts": "4", "sw": "2", "et": None}


def test_vim_with_set():
    opts = _parse_modeline_line("// vim: set ft=c ts=8 sw=8 noet :")
    assert opts == {"ft": "c", "ts": "8", "sw": "8", "noet": None}


def test_ex_prefix():
    opts = _parse_modeline_line("/* ex: set tabstop=2 : */")
    assert opts == {"tabstop": "2"}


def test_vi_prefix():
    opts = _parse_modeline_line("# vi: ts=2:sw=2")
    assert opts == {"ts": "2", "sw": "2"}


def test_versioned_vim_prefix():
    opts = _parse_modeline_line("# vim7: ft=python")
    assert opts == {"ft": "python"}


def test_unknown_options_ignored():
    opts = _parse_modeline_line("# vim: ft=python:foldmethod=marker:wrap")
    assert opts == {"ft": "python"}


def test_fileencoding_alias():
    opts = _parse_modeline_line("# vim: fenc=utf-8:fileencoding=latin-1")
    assert opts == {"fenc": "utf-8", "fileencoding": "latin-1"}


def test_must_be_preceded_by_whitespace_or_start():
    # "xvim:" must NOT be detected (no whitespace boundary).
    assert _parse_modeline_line("xvim: ft=python") is None


def test_modeline_at_start_of_line():
    opts = _parse_modeline_line("vim: ft=python")
    assert opts == {"ft": "python"}


def test_parse_modelines_first_lines():
    text = "# vim: ft=python ts=2 et\nprint('hi')\n"
    opts = parse_modelines(text, 5)
    assert opts.get("ft") == "python"
    assert opts.get("ts") == "2"


def test_parse_modelines_last_lines():
    text = "print('hi')\n" * 20 + "# vim: ft=python:ts=4\n"
    opts = parse_modelines(text, 5)
    assert opts.get("ft") == "python"
    assert opts.get("ts") == "4"


def test_parse_modelines_skips_middle():
    # Modeline in the middle is ignored when the file is large enough.
    middle_line = "# vim: ft=python\n"
    text = "a\n" * 10 + middle_line + "b\n" * 10
    opts = parse_modelines(text, 3)
    assert opts == {}


def test_parse_modelines_disabled():
    text = "# vim: ft=python\n"
    assert parse_modelines(text, 0) == {}


def test_set_form_options_split_on_whitespace_only():
    # Inside `set ... :`, ':' is the terminator and not a separator.
    opts = _parse_modeline_line("# vim: set ts=4 sw=4 et : trailing text")
    assert opts == {"ts": "4", "sw": "4", "et": None}
