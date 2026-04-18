"""
System clipboard integration using pyperclip.
"""

try:
    import pyperclip

    _pyperclip_available = True
except ImportError:
    _pyperclip_available = False


def copy_to_system_clipboard(text: str) -> None:
    """Copy text to the system clipboard via pyperclip."""
    if _pyperclip_available:
        try:
            pyperclip.copy(text)
        except pyperclip.PyperclipException:
            pass
