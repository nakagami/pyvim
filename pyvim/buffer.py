from prompt_toolkit import buffer
from prompt_toolkit.search import SearchDirection, SearchState
from prompt_toolkit.document import Document


class _VimBuffer(buffer.Buffer):
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
                self._editor.show_message(f'Search hit BOTTOM without match for: {text}')
            else:   # search BACKWARDS
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
                self._editor.show_message(f'Search hit TOP without match for: {text}')
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


buffer.Buffer = _VimBuffer
