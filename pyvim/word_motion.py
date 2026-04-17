"""
Character-by-character word motion functions matching vim behavior.

In vim:
- A "word" is a sequence of keyword characters (letters, digits, underscore),
  or a sequence of other non-blank characters (punctuation), separated by whitespace.
- A "WORD" is a sequence of non-blank characters, separated by whitespace.
- For non-ASCII characters, characters in different Unicode blocks (e.g. Hiragana,
  Katakana, CJK Ideographs) are treated as different character classes.
- Empty lines act as word boundaries.
"""

import unicodedata


# Character classes
_CLS_NEWLINE = -1
_CLS_WHITESPACE = 0
_CLS_WORD = 1
_CLS_PUNCT = 2
# Unicode block classes use their block start codepoint as class ID (>= 0x100)


def _char_class(ch, big_word=False):
    """Classify a character for vim word motion.

    Returns an integer class. Characters with the same class form one "word".
    """
    if ch == "\n":
        return _CLS_NEWLINE
    if ch.isspace():
        return _CLS_WHITESPACE
    if big_word:
        return _CLS_WORD

    cp = ord(ch)

    if cp < 0x100:
        # ASCII / Latin-1
        if ch.isalnum() or ch == "_":
            return _CLS_WORD
        return _CLS_PUNCT

    # CJK Unified Ideographs (+ Extensions, Compatibility)
    if (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0x20000 <= cp <= 0x2A6DF
        or 0xF900 <= cp <= 0xFAFF
    ):
        return 0x4E00

    # Hiragana
    if 0x3040 <= cp <= 0x309F:
        return 0x3040

    # Katakana (+ Phonetic Extensions + Halfwidth)
    if 0x30A0 <= cp <= 0x30FF or 0x31F0 <= cp <= 0x31FF or 0xFF65 <= cp <= 0xFF9F:
        return 0x30A0

    # Hangul Syllables (+ Jamo)
    if 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF:
        return 0xAC00

    # Fullwidth Latin letters and digits
    if 0xFF01 <= cp <= 0xFF5E:
        return 0xFF01

    # Fallback: use Unicode category
    cat = unicodedata.category(ch)
    if cat.startswith("L") or cat.startswith("N"):
        return _CLS_WORD
    return _CLS_PUNCT


def _is_whitespace_or_newline(cls):
    return cls == _CLS_WHITESPACE or cls == _CLS_NEWLINE


def w_forward(text, pos, count=1, big_word=False):
    """Return new cursor position after 'w' or 'W' motion."""
    text_len = len(text)
    for _ in range(count):
        if pos >= text_len:
            break

        cls = _char_class(text[pos], big_word)

        if cls == _CLS_NEWLINE:
            # On a newline: move past it
            pos += 1
        elif cls == _CLS_WHITESPACE:
            # On whitespace: skip whitespace, stop at next word or empty line
            while pos < text_len:
                c = _char_class(text[pos], big_word)
                if c == _CLS_NEWLINE:
                    pos += 1
                    break
                elif c == _CLS_WHITESPACE:
                    pos += 1
                else:
                    break
        else:
            # On word/punct: skip same class
            start_cls = cls
            while pos < text_len:
                c = _char_class(text[pos], big_word)
                if c != start_cls:
                    break
                pos += 1
            # Skip trailing whitespace (not across empty lines)
            while pos < text_len:
                c = _char_class(text[pos], big_word)
                if c == _CLS_WHITESPACE:
                    pos += 1
                elif c == _CLS_NEWLINE:
                    pos += 1
                    # If next is also newline (empty line), stop here
                    if pos >= text_len or text[pos] == "\n":
                        break
                    # If next is non-whitespace, stop (found the word)
                    if not text[pos].isspace():
                        break
                    # Otherwise continue skipping whitespace on next line
                else:
                    break

    return min(pos, text_len - 1) if text_len > 0 else 0


def b_backward(text, pos, count=1, big_word=False):
    """Return new cursor position after 'b' or 'B' motion."""
    for _ in range(count):
        if pos <= 0:
            break

        # Move back one position to look at char before cursor
        pos -= 1

        # Skip whitespace/newlines backwards, stopping at empty lines
        while pos > 0:
            c = _char_class(text[pos], big_word)
            if c == _CLS_NEWLINE:
                # Check if this is an empty line (prev char is also newline)
                if pos > 0 and text[pos - 1] == "\n":
                    break
                pos -= 1
            elif c == _CLS_WHITESPACE:
                pos -= 1
            else:
                break

        if pos <= 0:
            if pos == 0 and _is_whitespace_or_newline(_char_class(text[0], big_word)):
                pos = 0
            continue

        # If we stopped on a newline (empty line boundary), stay here
        cls = _char_class(text[pos], big_word)
        if _is_whitespace_or_newline(cls):
            continue

        # Now on a word/punct char. Find the start of this word.
        while pos > 0:
            prev_cls = _char_class(text[pos - 1], big_word)
            if prev_cls == cls:
                pos -= 1
            else:
                break

    return pos


def e_forward(text, pos, count=1, big_word=False):
    """Return new cursor position after 'e' or 'E' motion."""
    text_len = len(text)
    for _ in range(count):
        if pos >= text_len - 1:
            break

        # Move forward one position
        pos += 1

        # Skip whitespace/newlines
        while pos < text_len:
            c = _char_class(text[pos], big_word)
            if _is_whitespace_or_newline(c):
                pos += 1
            else:
                break

        if pos >= text_len:
            pos = text_len - 1
            break

        # Now on a word/punct char. Find the end of this word.
        cls = _char_class(text[pos], big_word)
        while pos < text_len - 1:
            next_cls = _char_class(text[pos + 1], big_word)
            if next_cls == cls:
                pos += 1
            else:
                break

    return min(pos, text_len - 1) if text_len > 0 else 0
