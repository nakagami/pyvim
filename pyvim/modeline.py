"""
Vim-compatible modeline parsing.

Modelines are a vim feature that allows embedding editor settings inside a
file. They are placed at the top or bottom of the file, in a comment.

Two forms are supported:

  Form 1 (no ``set``):
      [text]{white}{vi:|vim:|ex:}[white]{options}

      Options are separated by ``:`` or whitespace.

  Form 2 (with ``set``):
      [text]{white}{vi:|vim:|ex:}[white]se[t] {options}:[text]

      Options are separated by whitespace, and the modeline ends at the next
      ``:``.

Only a subset of vim options is honoured here:

  * ``fileencoding`` / ``fenc``
  * ``filetype`` / ``ft``
  * ``tabstop`` / ``ts``
  * ``shiftwidth`` / ``sw``
  * ``expandtab`` / ``et`` / ``noexpandtab`` / ``noet``
"""

import re

__all__ = ("parse_modelines", "apply_modeline_options")


_MODELINE_RE = re.compile(r"(?:^|\s)(?:ex|vi|vim\d*):\s*(.*)$")
_SET_RE = re.compile(r"^se(?:t)?\s+(.*?):.*$")

_VALID_OPTIONS = {
    "fileencoding",
    "fenc",
    "filetype",
    "ft",
    "tabstop",
    "ts",
    "shiftwidth",
    "sw",
    "expandtab",
    "et",
    "noexpandtab",
    "noet",
}


def _parse_modeline_line(line):
    """
    Parse one line. Return a dict of recognised options or ``None``.
    """
    m = _MODELINE_RE.search(line)
    if not m:
        return None

    rest = m.group(1).strip()
    if not rest:
        return None

    set_match = _SET_RE.match(rest)
    if set_match:
        tokens = set_match.group(1).split()
    else:
        tokens = []
        for part in rest.split(":"):
            tokens.extend(part.split())

    result = {}
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        if "=" in tok:
            name, _, value = tok.partition("=")
            name = name.strip()
            value = value.strip()
        else:
            name, value = tok.strip(), None

        if name not in _VALID_OPTIONS:
            continue
        result[name] = value
    return result or None


def parse_modelines(text, count):
    """
    Parse modelines from the first and last ``count`` lines of ``text``.

    Returns a dict of options (later modelines override earlier ones, matching
    vim, which scans top first then bottom).
    """
    if count <= 0 or not text:
        return {}

    lines = text.split("\n")
    n = len(lines)
    if n <= count * 2:
        candidates = lines
    else:
        candidates = lines[:count] + lines[-count:]

    options = {}
    for line in candidates:
        opts = _parse_modeline_line(line)
        if opts:
            options.update(opts)
    return options


def apply_modeline_options(buf, options):
    """
    Apply parsed modeline ``options`` to a ``VimBuffer``.

    Returns the new ``fileencoding`` value when the modeline requests an
    encoding change, otherwise ``None``.
    """
    new_encoding = None
    for name, value in options.items():
        if name in ("filetype", "ft"):
            if value:
                buf.filetype = value
        elif name in ("fileencoding", "fenc"):
            if value:
                new_encoding = value
        elif name in ("tabstop", "ts"):
            try:
                ivalue = int(value)
            except (TypeError, ValueError):
                continue
            if ivalue > 0:
                buf.tabstop = ivalue
        elif name in ("shiftwidth", "sw"):
            try:
                ivalue = int(value)
            except (TypeError, ValueError):
                continue
            if ivalue > 0:
                buf.shiftwidth = ivalue
        elif name in ("expandtab", "et"):
            buf.expand_tab = True
        elif name in ("noexpandtab", "noet"):
            buf.expand_tab = False
    return new_encoding
