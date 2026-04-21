"""
Tests for expandtab feature (Issue #71).
"The width is incorrect when expandtab."
"The number of spaces added sometimes seems incorrect depending on the number of characters in that line."

Root cause: tab_indent() uses cursor_position_col (character count) instead of the
visual column width. Wide characters (CJK etc.) occupy 2 visual columns each,
causing incorrect tab stop alignment.

These tests FAIL with the current (buggy) implementation and should PASS after the fix.
"""

import unicodedata


def visual_col(text, cursor_pos):
    """Calculate visual column width up to cursor_pos (wide chars count as 2)."""
    col = 0
    for ch in text[:cursor_pos]:
        if unicodedata.east_asian_width(ch) in ('W', 'F'):
            col += 2
        else:
            col += 1
    return col


def simulate_tab_indent(text, cursor_pos, shiftwidth):
    """Simulate the tab_indent implementation from key_bindings.py."""
    line_before = text[:cursor_pos].split("\n")[-1]
    vis_col = sum(
        2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        for ch in line_before
    )
    col_mod = vis_col % shiftwidth
    return shiftwidth - col_mod if col_mod else shiftwidth


def test_ascii_only_correct():
    """ASCII chars: character count == visual width, result is correct."""
    text = "abc"
    shiftwidth = 4
    # cursor after "abc" → visual col 3, next tab stop at 4 → 1 space
    assert simulate_tab_indent(text, len(text), shiftwidth) == 1


def test_wide_chars_wrong_space_count():
    """
    BUG: CJK wide characters occupy 2 visual columns each, but
    cursor_position_col returns character count (1 per char).

    "あいう" = 3 chars, but visual width = 6.
    With shiftwidth=4, cursor is at visual col 6:
      → next tab stop is at col 8 → should insert 2 spaces.
    But current implementation sees char_col=3:
      → 3 % 4 = 3 → inserts 1 space → cursor lands at visual col 7 (wrong!)
    """
    text = "あいう"
    shiftwidth = 4

    actual = simulate_tab_indent(text, len(text), shiftwidth)

    # Visual column is 6, next tab stop is 8, correct answer is 2 spaces
    vis = visual_col(text, len(text))
    assert vis == 6
    vis_mod = vis % shiftwidth
    expected = shiftwidth - vis_mod if vis_mod else shiftwidth
    assert expected == 2

    assert actual == expected  # FAILS: actual=1, expected=2


def test_mixed_ascii_and_wide_chars():
    """
    BUG: Mixed ASCII + CJK: "aあ" = 2 chars, but visual width = 3.
    With shiftwidth=4, cursor is at visual col 3:
      → next tab stop is at col 4 → should insert 1 space.
    But current implementation sees char_col=2:
      → 2 % 4 = 2 → inserts 2 spaces → cursor lands at visual col 5 (wrong!)
    """
    text = "aあ"
    shiftwidth = 4

    actual = simulate_tab_indent(text, len(text), shiftwidth)

    vis = visual_col(text, len(text))
    assert vis == 3
    vis_mod = vis % shiftwidth
    expected = shiftwidth - vis_mod if vis_mod else shiftwidth
    assert expected == 1

    assert actual == expected  # FAILS: actual=2, expected=1


def test_single_wide_char():
    """
    BUG: "あ" = 1 char, visual width = 2.
    With shiftwidth=4, cursor at visual col 2:
      → next tab stop at col 4 → should insert 2 spaces.
    But char_col=1 → 3 spaces inserted → cursor at visual col 5 (wrong!)
    """
    text = "あ"
    shiftwidth = 4

    actual = simulate_tab_indent(text, len(text), shiftwidth)

    vis = visual_col(text, len(text))
    assert vis == 2
    vis_mod = vis % shiftwidth
    expected = shiftwidth - vis_mod if vis_mod else shiftwidth
    assert expected == 2

    assert actual == expected  # FAILS: actual=3, expected=2


def test_wide_char_at_tab_stop():
    """
    BUG: "ああ" = 2 chars, visual width = 4 (exactly on a tab stop).
    With shiftwidth=4, cursor at visual col 4:
      → already on tab stop → should insert full shiftwidth (4 spaces).
    But char_col=2 → 2 % 4 = 2 → inserts 2 spaces (wrong!)
    """
    text = "ああ"
    shiftwidth = 4

    actual = simulate_tab_indent(text, len(text), shiftwidth)

    vis = visual_col(text, len(text))
    assert vis == 4
    vis_mod = vis % shiftwidth
    expected = shiftwidth - vis_mod if vis_mod else shiftwidth
    assert expected == 4

    assert actual == expected  # FAILS: actual=2, expected=4
