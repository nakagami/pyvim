from prompt_toolkit import buffer
from prompt_toolkit.search import SearchDirection, SearchState
from prompt_toolkit.document import Document

from .utils import getLogger

logger = getLogger()


def _new_text_and_position(self) -> tuple[str, int]:
    if self.complete_index is None:
        self.completion_start = 0
        self.completion_text = ""
        return self.original_document.text, self.original_document.cursor_position
    else:
        original_text_before_cursor = self.original_document.text_before_cursor
        original_text_after_cursor = self.original_document.text_after_cursor

        c = self.completions[self.complete_index]
        if c.start_position == 0:
            before = original_text_before_cursor
        else:
            before = original_text_before_cursor[: c.start_position]

        new_text = before + c.text + original_text_after_cursor
        new_cursor_position = len(before) + len(c.text)
        self.completion_start = c.start_position
        self.completion_text = c.text
        return new_text, new_cursor_position


buffer.CompletionState.new_text_and_position = _new_text_and_position


class VimBuffer(buffer.Buffer):
    def __init__(self, *args, **kwargs):
        editor = kwargs["editor"]
        del kwargs["editor"]
        super().__init__(*args, **kwargs)
        self._editor = editor
        self.mark = {}

        # Vi options.
        self._filetype = ""
        self._autoindent = None
        self._expand_tab = None
        self._tabstop = None
        self._shiftwidth = None
        self._encoding = None

    def _search(
        self,
        search_state: SearchState,
        include_current_position: bool = False,
        count: int = 1,
    ) -> tuple[int, int] | None:
        """
        Execute search. Return (working_index, cursor_position) tuple when this
        search is applied. Returns `None` when this text cannot be found.
        """
        assert count > 0

        text = search_state.text
        direction = search_state.direction
        ignore_case = self._editor.ignore_case

        def search_once(
            working_index: int, document: Document
        ) -> tuple[int, Document] | None:
            """
            Do search one time.
            Return (working_index, document) or `None`
            """
            if direction == SearchDirection.FORWARD:
                # Try find at the current input.
                new_index = document.find(
                    text,
                    include_current_position=include_current_position,
                    ignore_case=ignore_case,
                )

                if new_index is not None:
                    return (
                        working_index,
                        Document(document.text, document.cursor_position + new_index),
                    )
                elif self._editor.enable_wrapscan:
                    # No match, go forward in the history. (Include len+1 to wrap around.)
                    # (Here we should always include all cursor positions, because
                    # it's a different line.)
                    for i in range(working_index + 1, len(self._working_lines) + 1):
                        i %= len(self._working_lines)

                        document = Document(self._working_lines[i], 0)
                        new_index = document.find(
                            text, include_current_position=True, ignore_case=ignore_case
                        )
                        if new_index is not None:
                            return (i, Document(document.text, new_index))
                self._editor.show_message(
                    f"Search hit BOTTOM without match for: {text}"
                )
            else:  # search BACKWARDS
                # Try find at the current input.
                new_index = document.find_backwards(text, ignore_case=ignore_case)

                if new_index is not None:
                    return (
                        working_index,
                        Document(document.text, document.cursor_position + new_index),
                    )
                elif self._editor.enable_wrapscan:
                    # No match, go back in the history. (Include -1 to wrap around.)
                    for i in range(working_index - 1, -2, -1):
                        i %= len(self._working_lines)

                        document = Document(
                            self._working_lines[i], len(self._working_lines[i])
                        )
                        new_index = document.find_backwards(
                            text, ignore_case=ignore_case
                        )
                        if new_index is not None:
                            return (
                                i,
                                Document(document.text, len(document.text) + new_index),
                            )
                self._editor.show_message(f"Search hit TOP without match for: {text}")
            return None

        # Do 'count' search iterations.
        working_index = self.working_index
        document = self.document
        for _ in range(count):
            result = search_once(working_index, document)
            if result is None:
                return None  # Nothing found.
            else:
                working_index, document = result

        return (working_index, document.cursor_position)

    @property
    def filetype(self):
        return self._filetype

    @filetype.setter
    def filetype(self, v):
        self._filetype = v

    @property
    def autoindent(self):
        return self._editor.autoindent if self._autoindent is None else self._autoindent

    @autoindent.setter
    def autoindent(self, v):
        self._autoindent = v

    @property
    def expand_tab(self):
        return self._editor.expand_tab if self._expand_tab is None else self._expand_tab

    @expand_tab.setter
    def expand_tab(self, v):
        self._expand_tab = v

    @property
    def tabstop(self):
        return self._editor.tabstop if self._tabstop is None else self._tabstop

    @tabstop.setter
    def tabstop(self, v):
        self._tabstop = v

    @property
    def shiftwidth(self):
        return self._editor.shiftwidth if self._shiftwidth is None else self._shiftwidth

    @shiftwidth.setter
    def shiftwidth(self, v):
        self._shiftwidth = v

    @property
    def encoding(self):
        return self._editor.encoding if self._encoding is None else self._encoding

    @encoding.setter
    def encoding(self, v):
        self._encoding = v

    def get_options(self):
        return {
            "filetype": self.filetype,
            "expandtab": self.expand_tab,
            "tabstop": self.tabstop,
            "shiftwidth": self.shiftwidth,
            "encoding": self.encoding,
        }

    def undo(self):
        text = self.text
        super().undo()
        if self.text != text:
            self._undo_stack.append((text, self.cursor_position))

    def start_completion(self, *args, **kwargs):
        logger.debug("start_completion()")
        super().start_completion(*args, **kwargs)

    def complete_next(self, *args, **kwargs):
        logger.debug("complete_next()")
        super().complete_next(*args, **kwargs)

    def complete_previous(self, *args, **kwargs):
        logger.debug("complete_previous()")
        super().complete_previous(*args, **kwargs)

    def cancel_completion(self, *args, **kwargs):
        logger.debug("complete_cancel()")
        super().cancel_completion(*args, **kwargs)

    def _set_completions(self, *args, **kwargs):
        logger.debug("_set_completions()")
        super()._set_completions(*args, **kwargs)

    def start_history_lines_completion(self):
        logger.debug("start_history_lines_completion()")
        super().start_history_lines_completion()

    def go_to_completion(self, index):
        super().go_to_completion(index)
        s = self.complete_state
        logger.debug(
            f"go_to_completion({index}) completion_start={s.completion_start},completion_text={s.completion_text}"
        )
        self._editor.append_edit_completion(s.completion_start, s.completion_text)

    def apply_completion(self, *args, **kwargs):
        logger.debug("apply_completion()")
        super().apply_completion(*args, **kwargs)
