"""Tests for Document find and find_backwards monkey-patch in pyvim."""

from pyvim.document import Document


class TestDocumentFind:
    def test_find_forward_multiline(self):
        doc = Document(text="hello world\nfoo bar\nhello again", cursor_position=0)
        # Default include_current_position=False, so first hello at 0 is ignored
        pos = doc.find("hello")
        assert pos == 20  # relative offset to second 'hello'

    def test_find_include_current_position(self):
        doc = Document(text="hello world\nfoo bar\nhello again", cursor_position=0)
        pos = doc.find("hello", include_current_position=True)
        assert pos == 0

    def test_find_count(self):
        doc = Document(
            text="hello world\nhello again\nhello third", cursor_position=0
        )
        pos = doc.find("hello", count=2, include_current_position=True)
        assert pos == 12  # second 'hello' at index 12

    def test_find_in_current_line(self):
        doc = Document(text="hello world\nfoo bar\nhello again", cursor_position=0)
        assert doc.find("world", in_current_line=True) == 6
        assert doc.find("foo", in_current_line=True) is None

    def test_find_ignore_case(self):
        doc = Document(text="hello world\nfoo bar", cursor_position=0)
        assert doc.find("WORLD", ignore_case=False) is None
        assert doc.find("WORLD", ignore_case=True) == 6

    def test_find_not_found(self):
        doc = Document(text="hello world", cursor_position=0)
        assert doc.find("nonexistent") is None

    def test_find_at_end_of_document(self):
        doc = Document(text="hello world", cursor_position=11)
        assert doc.find("hello") is None


class TestDocumentFindBackwards:
    def test_find_backwards_multiline(self):
        doc = Document(text="hello world\nfoo bar\nhello again", cursor_position=25)
        pos = doc.find_backwards("hello")
        assert pos == -5  # cursor is at 25, 'hello' starts at 20 -> -5

    def test_find_backwards_count(self):
        doc = Document(
            text="hello world\nhello again\nhello third", cursor_position=29
        )
        # closest hello is at 24 (-5), previous is at 12 (-17), first is at 0 (-29)
        assert doc.find_backwards("hello", count=1) == -5
        assert doc.find_backwards("hello", count=2) == -17
        assert doc.find_backwards("hello", count=3) == -29

    def test_find_backwards_in_current_line(self):
        doc = Document(text="hello world\nfoo bar hello", cursor_position=25)
        assert doc.find_backwards("foo", in_current_line=True) == -13
        assert doc.find_backwards("world", in_current_line=True) is None

    def test_find_backwards_ignore_case(self):
        doc = Document(text="hello world\nfoo bar", cursor_position=15)
        assert doc.find_backwards("HELLO", ignore_case=False) is None
        assert doc.find_backwards("HELLO", ignore_case=True) == -15

    def test_find_backwards_not_found(self):
        doc = Document(text="hello world", cursor_position=5)
        assert doc.find_backwards("nonexistent") is None

    def test_find_backwards_at_start_of_document(self):
        doc = Document(text="hello world", cursor_position=0)
        assert doc.find_backwards("hello") is None
