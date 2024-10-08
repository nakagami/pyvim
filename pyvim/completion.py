import weakref
import jedi

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding.vi_state import InputMode

from .utils import getLogger

logger = getLogger()

__all__ = ("DocumentCompleter",)


class DocumentCompleter(Completer):
    """
    This is the general completer for EditorBuffer completions.
    Depending on the file type and settings, it selects another completer to
    call.
    """

    def __init__(self, editor, editor_buffer):
        # (Weakrefs, they are already pointing to us.)
        self._editor_ref = weakref.ref(editor)
        self._editor_buffer_ref = weakref.ref(editor_buffer)

    def get_completions(self, document, complete_event):
        editor = self._editor_ref()
        location = self._editor_buffer_ref().location or ".txt"

        if (
            location.endswith(".py")
            and editor.enable_jedi
            and editor.application.vi_state.input_mode == InputMode.INSERT
        ):
            completer = PythonCompleter(location)
            return completer.get_completions(document, complete_event)

        return []


class PythonCompleter(Completer):
    """
    Wrapper around the Jedi completion engine.
    """

    def __init__(self, location):
        self.location = location

    def get_completions(self, document, complete_event):
        try:
            script = jedi.Interpreter(
                document.text,
                path=self.location,
                namespaces=[locals(), globals()],
            )
        except Exception:
            return None

        if script:
            logger.debug(
                f'get_completions() line="{document.lines[document.cursor_position_row]}" col={document.cursor_position_col}'
            )
            try:
                completions = script.complete(
                    column=document.cursor_position_col,
                    line=document.cursor_position_row + 1,
                )
            except TypeError:
                # Issue #9: bad syntax causes completions() to fail in jedi.
                # https://github.com/jonathanslenders/python-prompt-toolkit/issues/9
                pass
            except UnicodeDecodeError:
                # Issue #43: UnicodeDecodeError on OpenBSD
                # https://github.com/jonathanslenders/python-prompt-toolkit/issues/43
                pass
            except AttributeError:
                # Jedi issue #513: https://github.com/davidhalter/jedi/issues/513
                pass
            except ValueError:
                # Jedi issue: "ValueError: invalid \x escape"
                pass
            except KeyError:
                # Jedi issue: "KeyError: u'a_lambda'."
                # https://github.com/jonathanslenders/ptpython/issues/89
                pass
            except IOError:
                # Jedi issue: "IOError: No such file or directory."
                # https://github.com/jonathanslenders/ptpython/issues/71
                pass
            else:
                logger.debug(f"screipt.complete() {len(completions)=}")
                completions = sorted(
                    completions,
                    key=lambda jc: (
                        # Private at the end.
                        jc.name.startswith("_"),
                        # Then sort by name.
                        jc.name_with_symbols.lower(),
                    ),
                )
                for c in completions:
                    if c.type == "function":
                        suffix = "()"
                    else:
                        suffix = ""

                    if c.type in ("param", "instance", "path"):
                        continue

                    # No completion until a key input.
                    if len(c.complete) - len(c.name_with_symbols) == 0:
                        continue

                    yield Completion(
                        c.name_with_symbols,
                        len(c.complete) - len(c.name_with_symbols),
                        display=c.name_with_symbols + suffix,
                    )
