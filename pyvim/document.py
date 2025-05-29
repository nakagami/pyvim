import re
from prompt_toolkit import document
from prompt_toolkit.document import Document
from .utils import re_finditer

# patch word forward regex
document._FIND_WORD_RE = re.compile(r"(\w+)")
document._FIND_CURRENT_WORD_RE = re.compile(r"^(\w+|\s+)")
document._FIND_CURRENT_WORD_INCLUDE_TRAILING_WHITESPACE_RE = re.compile(r"^((\w+)\s*)")


__all__ = ("Document",)


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
        return self.find_orig(
            sub, in_current_line, include_current_position, ignore_case, count
        )

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

    iterator = re_finditer(sub, self.text, flags)

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
        return self.find_backwards_orig(sub, in_current_line, ignore_case, count)
    text = self.text_before_cursor

    flags = re.MULTILINE
    if ignore_case:
        flags |= re.IGNORECASE
    iterator = re_finditer(sub, text, flags)

    matches = list(reversed(list(iterator)))
    if len(matches) < count:
        return None

    return matches[count - 1].start(0) - len(text)


Document.find_orig = Document.find
Document.find_backwards_orig = Document.find_backwards

Document.find = _document_find
Document.find_backwards = _document_find_backwards
