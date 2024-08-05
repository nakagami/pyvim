from prompt_toolkit.keys import Keys
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding.key_processor import KeyProcessor, KeyPress, _Flush


class VimKeyProcessor(KeyProcessor):
    def __init__(self, key_bindings, editor):
        super().__init__(key_bindings)
        self._editor = editor

    def process_keys(self) -> None:
        """
        Process all the keys in the `input_queue`.
        (To be called after `feed`.)

        Note: because of the `feed`/`process_keys` separation, it is
              possible to call `feed` from inside a key binding.
              This function keeps looping until the queue is empty.
        """
        app = get_app()

        def not_empty() -> bool:
            # When the application result is set, stop processing keys.  (E.g.
            # if ENTER was received, followed by a few additional key strokes,
            # leave the other keys in the queue.)
            if app.is_done:
                # But if there are still CPRResponse keys in the queue, these
                # need to be processed.
                return any(k for k in self.input_queue if k.key == Keys.CPRResponse)
            else:
                return bool(self.input_queue)

        def get_next() -> KeyPress:
            if app.is_done:
                # Only process CPR responses. Everything else is typeahead.
                cpr = [k for k in self.input_queue if k.key == Keys.CPRResponse][0]
                self.input_queue.remove(cpr)
                return cpr
            else:
                return self.input_queue.popleft()

        is_flush = False

        while not_empty():
            # Process next key.
            key_press = get_next()

            is_flush = key_press is _Flush
            is_cpr = key_press.key == Keys.CPRResponse

            if not is_flush and not is_cpr:
                self.before_key_press.fire()

            try:
                self._process_coroutine.send(key_press)
            except Exception:
                # If for some reason something goes wrong in the parser, (maybe
                # an exception was raised) restart the processor for next time.
                self.reset()
                self.empty_queue()
                raise

            self._editor.append_edit_command(key_press)

            if not is_flush and not is_cpr:
                self.after_key_press.fire()

        # Skip timeout if the last key was flush.
        if not is_flush:
            self._start_timeout()

    def _call_handler(self, handler, key_sequence):
        # monkey patch. Don't save to undo stack per key press.
        handler.save_before = lambda a: False
        super()._call_handler(handler, key_sequence)
