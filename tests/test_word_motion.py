"""Tests for word motion functions (w, b, e, W, B, E)."""

from pyvim.word_motion import w_forward, b_backward, e_forward


class TestWForward:
    """Tests for w (word forward) motion."""

    def test_simple_words(self):
        text = "hello world"
        assert w_forward(text, 0) == 6  # h -> w

    def test_word_to_punct(self):
        text = "hello, world"
        assert w_forward(text, 0) == 5  # h -> ,

    def test_punct_to_word(self):
        text = "hello, world"
        assert w_forward(text, 5) == 7  # , -> w

    def test_multiple_spaces(self):
        text = "hello   world"
        assert w_forward(text, 0) == 8  # h -> w

    def test_at_end(self):
        text = "hello"
        assert w_forward(text, 4) == 4  # stays at end

    def test_newline(self):
        text = "hello\nworld"
        assert w_forward(text, 0) == 6  # h -> w on next line

    def test_empty_line_stops(self):
        text = "hello\n\nworld"
        assert w_forward(text, 0) == 6  # h -> empty line
        assert w_forward(text, 6) == 7  # empty line -> w

    def test_count(self):
        text = "one two three"
        assert w_forward(text, 0, count=2) == 8  # o -> t(hree)

    def test_on_space(self):
        text = "hello world"
        assert w_forward(text, 5) == 6  # space -> w

    def test_mixed_punct(self):
        text = "a=b+c"
        assert w_forward(text, 0) == 1  # a -> =
        assert w_forward(text, 1) == 2  # = -> b
        assert w_forward(text, 2) == 3  # b -> +

    def test_cjk_each_block_is_word(self):
        text = "漢字ひらがな"
        assert w_forward(text, 0) == 2  # 漢字 -> ひらがな

    def test_cjk_to_ascii(self):
        text = "漢字abc"
        assert w_forward(text, 0) == 2  # 漢字 -> a

    def test_ascii_to_cjk(self):
        text = "abc漢字"
        assert w_forward(text, 0) == 3  # abc -> 漢

    def test_hiragana_katakana_separate(self):
        text = "あいうアイウ"
        assert w_forward(text, 0) == 3  # hiragana -> katakana


class TestWForwardBigWord:
    """Tests for W (WORD forward) motion."""

    def test_simple(self):
        text = "hello world"
        assert w_forward(text, 0, big_word=True) == 6

    def test_punct_not_boundary(self):
        text = "hello,world next"
        assert w_forward(text, 0, big_word=True) == 12  # hello,world -> next

    def test_mixed(self):
        text = "a=b c"
        assert w_forward(text, 0, big_word=True) == 4  # a=b -> c


class TestBBackward:
    """Tests for b (word backward) motion."""

    def test_simple_words(self):
        text = "hello world"
        assert b_backward(text, 6) == 0  # w -> h

    def test_word_before_punct(self):
        text = "hello, world"
        assert b_backward(text, 7) == 5  # w -> ,
        assert b_backward(text, 5) == 0  # , -> h

    def test_multiple_spaces(self):
        text = "hello   world"
        assert b_backward(text, 8) == 0

    def test_at_start(self):
        text = "hello"
        assert b_backward(text, 0) == 0

    def test_newline(self):
        text = "hello\nworld"
        assert b_backward(text, 6) == 0

    def test_empty_line(self):
        text = "hello\n\nworld"
        assert b_backward(text, 7) == 6  # w -> empty line (newline position)

    def test_count(self):
        text = "one two three"
        assert b_backward(text, 8, count=2) == 0

    def test_mixed_punct(self):
        text = "a=b+c"
        assert b_backward(text, 4) == 3  # c -> +
        assert b_backward(text, 3) == 2  # + -> b
        assert b_backward(text, 2) == 1  # b -> =

    def test_cjk(self):
        text = "漢字ひらがな"
        assert b_backward(text, 3) == 2  # ら -> ひ (start of hiragana block)
        assert b_backward(text, 2) == 0  # ひ -> 漢 (start of kanji block)


class TestBBackwardBigWord:
    """Tests for B (WORD backward) motion."""

    def test_simple(self):
        text = "hello world"
        assert b_backward(text, 6, big_word=True) == 0

    def test_punct_not_boundary(self):
        text = "hello,world next"
        assert b_backward(text, 12, big_word=True) == 0


class TestEForward:
    """Tests for e (end of word) motion."""

    def test_simple_words(self):
        text = "hello world"
        assert e_forward(text, 0) == 4  # h -> o (end of hello)

    def test_at_end_of_word(self):
        text = "hello world"
        assert e_forward(text, 4) == 10  # o -> d (end of world)

    def test_punct(self):
        text = "hello, world"
        assert e_forward(text, 0) == 4  # h -> o
        assert e_forward(text, 4) == 5  # o -> ,

    def test_newline(self):
        text = "hello\nworld"
        assert e_forward(text, 4) == 10

    def test_count(self):
        text = "one two three"
        assert e_forward(text, 0, count=2) == 6

    def test_cjk(self):
        text = "漢字ひらがな"
        assert e_forward(text, 0) == 1  # 漢 -> 字 (end of kanji word)

    def test_at_end(self):
        text = "hello"
        assert e_forward(text, 4) == 4  # stays at end


class TestEForwardBigWord:
    """Tests for E (end of WORD) motion."""

    def test_simple(self):
        text = "hello world"
        assert e_forward(text, 0, big_word=True) == 4

    def test_punct_not_boundary(self):
        text = "hello,world next"
        assert e_forward(text, 0, big_word=True) == 10  # -> d (end of hello,world)
