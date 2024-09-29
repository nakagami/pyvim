from typing import Callable, TypeVar
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.key_binding.bindings.vi import TextObject, TextObjectType
from prompt_toolkit.filters import Always, Filter
from prompt_toolkit.filters.app import (
    vi_navigation_mode,
    vi_selection_mode,
    vi_waiting_for_text_object_mode,
)
from prompt_toolkit.selection import SelectionType
from prompt_toolkit.keys import Keys


E = KeyPressEvent

TextObjectFunction = Callable[[E], TextObject]
_TOF = TypeVar("_TOF", bound=TextObjectFunction)


def create_text_object_decorator(
    key_bindings: KeyBindings,
) -> Callable[..., Callable[[_TOF], _TOF]]:
    """
    Create a decorator that can be used to register Vi text object implementations.
    """

    def text_object_decorator(
        *keys: Keys | str,
        filter: Filter = Always(),
        no_move_handler: bool = False,
        no_selection_handler: bool = False,
        eager: bool = False,
    ) -> Callable[[_TOF], _TOF]:
        """
        Register a text object function.

        Usage::

            @text_object('w', filter=..., no_move_handler=False)
            def handler(event):
                # Return a text object for this key.
                return TextObject(...)

        :param no_move_handler: Disable the move handler in navigation mode.
            (It's still active in selection mode.)
        """

        def decorator(text_object_func: _TOF) -> _TOF:
            @key_bindings.add(
                *keys, filter=vi_waiting_for_text_object_mode & filter, eager=eager
            )
            def _apply_operator_to_text_object(event: E) -> None:
                # Arguments are multiplied.
                vi_state = event.app.vi_state
                event._arg = str((vi_state.operator_arg or 1) * (event.arg or 1))

                # Call the text object handler.
                text_obj = text_object_func(event)

                # Get the operator function.
                # (Should never be None here, given the
                # `vi_waiting_for_text_object_mode` filter state.)
                operator_func = vi_state.operator_func

                operator_func(event, text_obj)

                # Clear operator.
                event.app.vi_state.operator_func = None
                event.app.vi_state.operator_arg = None

            # Register a move operation. (Doesn't need an operator.)
            if not no_move_handler:

                @key_bindings.add(
                    *keys,
                    filter=~vi_waiting_for_text_object_mode & filter & vi_navigation_mode,
                    eager=eager,
                )
                def _move_in_navigation_mode(event: E) -> None:
                    """
                    Move handler for navigation mode.
                    """
                    text_object = text_object_func(event)
                    event.current_buffer.cursor_position += text_object.start

            # Register a move selection operation.
            if not no_selection_handler:

                @key_bindings.add(
                    *keys,
                    filter=~vi_waiting_for_text_object_mode
                    & filter
                    & vi_selection_mode,
                    eager=eager,
                )
                def _move_in_selection_mode(event: E) -> None:
                    """
                    Move handler for selection mode.
                    """
                    text_object = text_object_func(event)
                    buff = event.current_buffer
                    selection_state = buff.selection_state

                    if selection_state is None:
                        return  # Should not happen, because of the `vi_selection_mode` filter.

                    # When the text object has both a start and end position, like 'i(' or 'iw',
                    # Turn this into a selection, otherwise the cursor.
                    if text_object.end:
                        # Take selection positions from text object.
                        start, end = text_object.operator_range(buff.document)
                        start += buff.cursor_position
                        end += buff.cursor_position

                        selection_state.original_cursor_position = start
                        buff.cursor_position = end

                        # Take selection type from text object.
                        if text_object.type == TextObjectType.LINEWISE:
                            selection_state.type = SelectionType.LINES
                        else:
                            selection_state.type = SelectionType.CHARACTERS
                    else:
                        event.current_buffer.cursor_position += text_object.start

            # Make it possible to chain @text_object decorators.
            return text_object_func

        return decorator

    return text_object_decorator
