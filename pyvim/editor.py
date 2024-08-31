"""
The main editor class.

Usage::

    files_to_edit = ['file1.txt', 'file2.py']
    e = Editor(files_to_edit)
    e.run()  # Runs the event loop, starts interaction.
"""
from prompt_toolkit.application import Application
from prompt_toolkit.application.application import _CombinedRegistry
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import Condition
from prompt_toolkit.history import FileHistory
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles import DynamicStyle
from prompt_toolkit.key_binding.vi_state import InputMode

from .commands.completer import create_command_completer
from .commands.handler import handle_command
from .commands.preview import CommandPreviewer
from .help import HELP_TEXT
from .key_bindings import create_key_bindings
from .layout import EditorLayout
from .style import generate_built_in_styles, get_editor_style_by_name
from .window_arrangement import WindowArrangement
from .io import FileIO, DirectoryIO, HttpIO, GZipFileIO
from .key_processor import VimKeyProcessor
from .utils import getLogger

import pygments
import os

__all__ = (
    'Editor',
)


logger = getLogger()


class Editor(object):
    """
    The main class. Containing the whole editor.

    :param config_directory: Place where configuration is stored.
    :param input: (Optionally) `prompt_toolkit.input.Input` object.
    :param output: (Optionally) `prompt_toolkit.output.Output` object.
    """
    def __init__(self, config_directory='~/.pyvim', input=None, output=None):
        self.input = input
        self.output = output

        # Vi options.
        self.show_line_numbers = False
        self.highlight_search = True
        self.paste_mode = False
        self.show_ruler = True
        self.show_wildmenu = True
        self.expand_tab = True  # Insect spaces instead of tab characters.
        self.tabstop = 4  # Number of spaces that a tab character represents.
        self.shiftwidth = 4  # Number of spaces at indent/unindent
        self.incsearch = True  # Show matches while typing search string.
        self.ignore_case = False  # Ignore case while searching.
        self.enable_mouse_support = False
        self.display_unprintable_characters = True  # ':set list'
        self.enable_jedi = True  # ':set jedi', for Python Jedi completion.
        self.enable_wrapscan = True  # ':set ws', Search wrap scan.
        self.scroll_offset = 0  # ':set scrolloff'
        self.relative_number = False  # ':set relativenumber'
        self.wrap_lines = True  # ':set wrap'
        self.break_indent = False  # ':set breakindent'
        self.cursorline = False  # ':set cursorline'
        self.cursorcolumn = False  # ':set cursorcolumn'
        self.colorcolumn = []  # ':set colorcolumn'. List of integers.
        # locations in command argument
        self.locations = []
        self.current_location_index = 0
        # open file history
        self.location_history = []

        self.on_open_buffer = None

        # Ensure config directory exists.
        self.config_directory = os.path.abspath(os.path.expanduser(config_directory))
        if not os.path.exists(self.config_directory):
            os.mkdir(self.config_directory)

        self.window_arrangement = WindowArrangement(self)
        self.message = None

        # Load styles. (Mapping from name to Style class.)
        self.styles = generate_built_in_styles()
        self.current_style = get_editor_style_by_name('vim')

        # I/O backends.
        self.io_backends = [
            DirectoryIO(),
            HttpIO(),
            GZipFileIO(),  # Should come before FileIO.
            FileIO(),
        ]

        # Create history and search buffers.
        def handle_action(buff):
            ' When enter is pressed in the Vi command line. '
            text = buff.text  # Remember: leave_command_mode resets the buffer.

            # First leave command mode. We want to make sure that the working
            # pane is focussed again before executing the command handlers.
            self.leave_command_mode(append_to_history=True)

            # Execute command.
            handle_command(self, text)

        commands_history = FileHistory(os.path.join(self.config_directory, 'commands_history'))
        self.command_buffer = Buffer(
            accept_handler=handle_action,
            enable_history_search=True,
            completer=create_command_completer(self),
            history=commands_history,
            multiline=False)

        search_buffer_history = FileHistory(os.path.join(self.config_directory, 'search_history'))
        self.search_buffer = Buffer(
            history=search_buffer_history,
            enable_history_search=True,
            multiline=False)

        # Create key bindings registry.
        self.key_bindings = create_key_bindings(self)

        # Create layout and CommandLineInterface instance.
        self.editor_layout = EditorLayout(self, self.window_arrangement)
        self.application = self._create_application()

        # Hide message when a key is pressed.
        def key_pressed(_):
            self.message = None
        self.application.key_processor.before_key_press += key_pressed

        # Command line previewer.
        self.previewer = CommandPreviewer(self)

        self.last_substitute_text = ''

        self._last_edit_command = []
        self._in_edit_command = False

    def load_initial_files(self, locations, in_tab_pages=False, hsplit=False, vsplit=False):
        """
        Load a list of files.
        """
        assert in_tab_pages + hsplit + vsplit <= 1  # Max one of these options.

        # When no files were given, open at least one empty buffer.
        locations2 = locations or [None]

        # First file
        self.window_arrangement.open_buffer(locations2[0])

        for f in locations2[1:]:
            if in_tab_pages:
                self.window_arrangement.create_tab(f)
            elif hsplit:
                self.window_arrangement.hsplit(location=f)
            elif vsplit:
                self.window_arrangement.vsplit(location=f)
            else:
                self.window_arrangement.open_buffer(f)

        self.window_arrangement.active_tab_index = 0

        if locations and len(locations) > 1:
            self.show_message('%i files loaded.' % len(locations))
            self.locations = locations
            self.current_location_index = 0

    def _create_application(self):
        """
        Create CommandLineInterface instance.
        """
        # Create Application.
        application = Application(
            input=self.input,
            output=self.output,
            editing_mode=EditingMode.VI,
            layout=self.editor_layout.layout,
            key_bindings=self.key_bindings,
            style=DynamicStyle(lambda: self.current_style),
            paste_mode=Condition(lambda: self.paste_mode),
            include_default_pygments_style=False,
            mouse_support=Condition(lambda: self.enable_mouse_support),
            full_screen=True,
            enable_page_navigation_bindings=True)
        application.key_processor = VimKeyProcessor(_CombinedRegistry(application), self)

        # Handle command line previews.
        # (e.g. when typing ':colorscheme blue', it should already show the
        # preview before pressing enter.)
        def preview(_):
            if self.application.layout.has_focus(self.command_buffer):
                self.previewer.preview(self.command_buffer.text)
        self.command_buffer.on_text_changed += preview

        return application

    @property
    def current_editor_buffer(self):
        """
        Return the `EditorBuffer` that is currently active.
        """
        current_buffer = self.application.current_buffer

        # Find/return the EditorBuffer with this name.
        for b in self.window_arrangement.editor_buffers:
            if b.buffer == current_buffer:
                return b

    @property
    def add_key_binding(self):
        """
        Shortcut for adding new key bindings.
        (Mostly useful for a pyvimrc file, that receives this Editor instance
        as input.)
        """
        return self.key_bindings.add

    def show_message(self, message):
        """
        Set a warning message. The layout will render it as a "pop-up" at the
        bottom.
        """
        self.message = message

    def use_colorscheme(self, name='default'):
        """
        Apply new colorscheme. (By name.)
        """
        try:
            self.current_style = get_editor_style_by_name(name)
        except pygments.util.ClassNotFound:
            pass

    def sync_with_prompt_toolkit(self):
        """
        Update the prompt-toolkit Layout and FocusStack.
        """
        # After executing a command, make sure that the layout of
        # prompt-toolkit matches our WindowArrangement.
        self.editor_layout.update()

        # Make sure that the focus stack of prompt-toolkit has the current
        # page.
        window = self.window_arrangement.active_pt_window
        if window:
            self.application.layout.focus(window)

    def show_help(self):
        """
        Show help in new window.
        """
        self.window_arrangement.hsplit(text=HELP_TEXT)
        self.sync_with_prompt_toolkit()  # Show new window.

    def get_options(self):
        return {
            "hlsearch": self.highlight_search,
            "paste": self.paste_mode,
            "ruler": self.show_ruler,
            "wildmenu": self.show_wildmenu,
            "expandtab": self.expand_tab,
            "tabstop": self.tabstop,
            "shiftwidth": self.shiftwidth,
            "scrolloff": self.scroll_offset,
            "incsearch": self.incsearch,
            "ignorecase": self.ignore_case,
            "list": self.display_unprintable_characters,
            "jedi": self.enable_jedi,
            "wrapscan": self.enable_wrapscan,
            "relativenumber": self.relative_number,
            "wrap": self.wrap_lines,
            "breakindent": self.break_indent,
            "mouse": self.enable_mouse_support,
            "tildeop": self.application.vi_state.tilde_operator,
            "cursorline": self.cursorline,
            "corsorcolumn": self.cursorcolumn,
            "colorcolumn": self.colorcolumn,
        }

    def get_current_buffer_options(self):
        return self.get_options() | self.application.current_buffer.get_options()

    def run(self):
        """
        Run the event loop for the interface.
        This starts the interaction.
        """
        # Make sure everything is in sync, before starting.
        self.sync_with_prompt_toolkit()

        def pre_run():
            # Start in navigation mode.
            self.application.vi_state.input_mode = InputMode.NAVIGATION

        # Run eventloop of prompt_toolkit.
        self.application.run(pre_run=pre_run)

    def enter_command_mode(self):
        """
        Go into command mode.
        """
        self.application.layout.focus(self.command_buffer)
        self.application.vi_state.input_mode = InputMode.INSERT

        self.previewer.save()

    def leave_command_mode(self, append_to_history=False):
        """
        Leave command mode. Focus document window again.
        """
        self.previewer.restore()

        self.application.layout.focus_last()
        self.application.vi_state.input_mode = InputMode.NAVIGATION

        self.command_buffer.reset(append_to_history=append_to_history)

    def start_edit_command(self, event=None):
        if event:
            self._last_edit_command = event.key_sequence[:]
        else:
            self._last_edit_command = []
        self.application.current_buffer.save_to_undo_stack()
        self._in_edit_command = True
        logger.debug(f"start_edit_command():{self.application.vi_state.input_mode}:{event}")
        logger.debug(self._last_edit_command)

    def append_edit_command(self, key_event):
        if self._in_edit_command:
            if key_event.key in (Keys.ControlG, Keys.ControlP, Keys.ControlN):
                return
            self._last_edit_command.append(key_event)
            logger.debug(f"append_edit_command():{self.application.vi_state.input_mode}:{key_event}")
            logger.debug(self._last_edit_command)

    def append_edit_completion(self, start, text):
        if self._in_edit_command:
            logger.debug(f"append_edit_completion():{start}:{text}")
            if isinstance(self._last_edit_command[-1], tuple):
                self._last_edit_commit.pop()
            self._last_edit_command.append((start, text))
            logger.debug(self._last_edit_command)

    def finish_edit_command(self, event=None):
        if self._in_edit_command:
            if event:
                self._last_edit_command.extend(event.key_sequence)
            logger.debug(f"finish_edit_command():{self.application.vi_state.input_mode}:{event}")
            logger.debug(self._last_edit_command)
        self._in_edit_command = False

    def last_edit_command(self):
        # TODO: Convert completion string to keypress event
        return self._last_edit_command[:]

    def replay_edit_command(self):
        logger.debug("replay_edit_command")
        logger.debug(self._last_edit_command)
        self.application.key_processor.feed_multiple(self.last_edit_command())
