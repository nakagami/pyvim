import os
import re
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.application.current import get_app
from prompt_toolkit.clipboard import ClipboardData
from prompt_toolkit.selection import SelectionType
from prompt_toolkit.document import Document
from ..lexer import DocumentLexer


__all__ = (
    'has_command_handler',
    'call_command_handler',
)


COMMANDS_TO_HANDLERS = {}  # Global mapping Vi commands to their handler.
COMMANDS_TAKING_LOCATIONS = set()  # Name of commands that accept locations.
SET_COMMANDS = {}  # Mapping ':set'-commands to their handler.
SET_COMMANDS_TAKING_VALUE = set()


_NO_WRITE_SINCE_LAST_CHANGE_TEXT = 'No write since last change (add ! to override)'
_NO_FILE_NAME = 'No file name'


def has_command_handler(command):
    return command in COMMANDS_TO_HANDLERS


def call_command_handler(command, editor, variables):
    """
    Execute command.
    """
    COMMANDS_TO_HANDLERS[command](editor, variables)


def get_commands():
    return COMMANDS_TO_HANDLERS.keys()


def get_commands_taking_locations():
    return COMMANDS_TAKING_LOCATIONS


# Decorators

def _cmd(name):
    """
    Base decorator for registering commands in this namespace.
    """
    def decorator(func):
        COMMANDS_TO_HANDLERS[name] = func
        return func
    return decorator


def location_cmd(name, accepts_force=False):
    """
    Decorator that registers a command that takes a location as (optional)
    parameter.
    """
    COMMANDS_TAKING_LOCATIONS.add(name)

    def decorator(func):
        @_cmd(name)
        def command_wrapper(editor, variables):
            location = variables.get('location')
            force = bool(variables['force'])

            if force and not accepts_force:
                editor.show_message('No ! allowed')
            elif accepts_force:
                func(editor, location, force=force)
            else:
                func(editor, location)
        return func
    return decorator


def cmd(name, accepts_force=False):
    """
    Decarator that registers a command that doesn't take any parameters.
    """
    def decorator(func):
        @_cmd(name)
        def command_wrapper(editor, variables):
            force = bool(variables['force'])

            if force and not accepts_force:
                editor.show_message('No ! allowed')
            elif accepts_force:
                func(editor, force=force)
            else:
                func(editor)
        return func
    return decorator


def set_cmd(name, accepts_value=False):
    """
    Docorator that registers a ':set'-command.
    """
    def decorator(func):
        SET_COMMANDS[name] = func
        if accepts_value:
            SET_COMMANDS_TAKING_VALUE.add(name)
        return func
    return decorator


# Actual command implementations

@_cmd('set')
def set_command_execute(editor, variables):
    """
    Execute a ':set' command.
    """
    option = variables.get('set_option')
    value = variables.get('set_value')

    if option in SET_COMMANDS:
        # Call the correct handler.
        if option in SET_COMMANDS_TAKING_VALUE:
            SET_COMMANDS[option](editor, value)
        else:
            SET_COMMANDS[option](editor)
    else:
        editor.show_message('Unknown option: %s' % option)


@cmd('bn', accepts_force=True)
def _bn(editor, force=False):
    """
    Go to next buffer.
    """
    eb = editor.window_arrangement.active_editor_buffer

    if not force and eb.has_unsaved_changes:
        editor.show_message(_NO_WRITE_SINCE_LAST_CHANGE_TEXT)
    else:
        editor.window_arrangement.go_to_next_buffer()


@cmd('bp', accepts_force=True)
def _bp(editor, force=False):
    """
    Go to previous buffer.
    """
    eb = editor.window_arrangement.active_editor_buffer

    if not force and eb.has_unsaved_changes:
        editor.show_message(_NO_WRITE_SINCE_LAST_CHANGE_TEXT)
    else:
        editor.window_arrangement.go_to_previous_buffer()


@cmd('only')
def only(editor):
    """
    Keep only the current window.
    """
    editor.window_arrangement.keep_only_current_window()


@cmd('hide')
def hide(editor):
    """
    Hide the current window.
    """
    editor.window_arrangement.close_window()


@location_cmd('sp')
@location_cmd('split')
def horizontal_split(editor, location):
    """
    Split window horizontally.
    """
    editor.window_arrangement.hsplit(location or None)


@location_cmd('vsp')
@location_cmd('vsplit')
def vertical_split(editor, location):
    """
    Split window vertically.
    """
    editor.window_arrangement.vsplit(location or None)


@cmd('new')
def new_buffer(editor):
    """
    Create new buffer.
    """
    editor.window_arrangement.hsplit(new=True)


@cmd('vnew')
def new_vertical_buffer(editor):
    """
    Create new buffer, splitting vertically.
    """
    editor.window_arrangement.vsplit(new=True)


@location_cmd('badd')
def buffer_add(editor, location):
    """
    Add a new buffer.
    """
    editor.window_arrangement.open_buffer(location)


@cmd('files')
@cmd('ls')
@cmd('buffers')
def buffer_list(editor):
    """
    List all buffers.
    """
    def handler():
        wa = editor.window_arrangement
        for info in wa.list_open_buffers():
            char = '%' if info.is_active else ''
            eb = info.editor_buffer
            print(' %3i %-2s %-20s  line %i' % (
                  info.index, char, eb.location, (eb.buffer.document.cursor_position_row + 1)))
        input('\nPress ENTER to continue...')
    run_in_terminal(handler)


@_cmd('b')
@_cmd('buffer')
def _buffer(editor, variables, force=False):
    """
    Go to one of the open buffers.
    """
    eb = editor.window_arrangement.active_editor_buffer
    force = bool(variables['force'])

    buffer_name = variables.get('buffer_name')
    if buffer_name:
        if not force and eb.has_unsaved_changes:
            editor.show_message(_NO_WRITE_SINCE_LAST_CHANGE_TEXT)
        else:
            editor.window_arrangement.go_to_buffer(buffer_name)


@cmd('bw', accepts_force=True)
@cmd('bd', accepts_force=True)
def buffer_wipe(editor, force=False):
    """
    Wipe buffer.
    """
    eb = editor.window_arrangement.active_editor_buffer
    if not force and eb.has_unsaved_changes:
        editor.show_message(_NO_WRITE_SINCE_LAST_CHANGE_TEXT)
    else:
        editor.window_arrangement.close_buffer()


@location_cmd('o', accepts_force=True)
@location_cmd('open', accepts_force=True)
@location_cmd('e', accepts_force=True)
@location_cmd('edit', accepts_force=True)
def buffer_edit(editor, location, force=False):
    """
    Edit new buffer.
    """
    if location is None:
        # Edit/open without a location will reload the current file, if there are
        # no changes.
        eb = editor.window_arrangement.active_editor_buffer
        if eb.location is None:
            editor.show_message(_NO_FILE_NAME)
        elif not force and eb.has_unsaved_changes:
            editor.show_message(_NO_WRITE_SINCE_LAST_CHANGE_TEXT)
        else:
            eb.reload()
    else:
        if len(editor.location_history) > 1:
            location = location.replace("#", editor.location_history[-2])
        editor.file_explorer = ''
        editor.window_arrangement.open_buffer(location, show_in_current_window=True)


def _open_from_nth_location(editor, n: int):
    """
    Edit n-th location.
    """
    if len(editor.locations) < 1:
        editor.show_message("There is only one file to edit")
        return
    if n < 0 or len(editor.locations) <= n:
        editor.show_message("No more file")
        return
    editor.file_explorer = ''
    editor.window_arrangement.open_buffer(editor.locations[n], show_in_current_window=True)
    editor.current_location_index = n


@location_cmd('n', accepts_force=True)
@location_cmd('next', accepts_force=True)
def next_file(editor, location, force=False):
    _open_from_nth_location(editor, editor.current_location_index + 1)


@location_cmd('p', accepts_force=True)
@location_cmd('previous', accepts_force=True)
def previous_file(editor, location, force=False):
    _open_from_nth_location(editor, editor.current_location_index - 1)


@cmd('q', accepts_force=True)
@cmd('quit', accepts_force=True)
def quit(editor, force=False):
    """
    Quit.
    """
    eb = editor.window_arrangement.active_editor_buffer
    eb_is_open_in_another_window = len(list(editor.window_arrangement.get_windows_for_buffer(eb))) > 1
    if not force and eb.has_unsaved_changes and not eb_is_open_in_another_window:
        editor.show_message(_NO_WRITE_SINCE_LAST_CHANGE_TEXT)
    elif editor.window_arrangement.active_tab.window_count() == 1 and len(editor.window_arrangement.tab_pages) == 1:
        editor.application.exit()
    else:
        editor.window_arrangement.close_window()


@cmd('qa', accepts_force=True)
@cmd('qall', accepts_force=True)
def quit_all(editor, force=False):
    """
    Quit all.
    """
    ebs = editor.window_arrangement.editor_buffers
    if not force and any(eb.has_unsaved_changes for eb in ebs):
        editor.show_message(_NO_WRITE_SINCE_LAST_CHANGE_TEXT)
    else:
        editor.application.exit()


@location_cmd('w', accepts_force=True)
@location_cmd('write', accepts_force=True)
def write(editor, location, force=False):
    """
    Write file.
    """
    if location and not force and os.path.exists(location):
        editor.show_message('File exists (add ! to overriwe)')
    else:
        eb = editor.window_arrangement.active_editor_buffer
        if location is None and eb.location is None:
            editor.show_message(_NO_FILE_NAME)
        else:
            eb.write(location, force)


@location_cmd('wq', accepts_force=True)
def write_and_quit(editor, location, force=False):
    """
    Write file and quit.
    """
    write(editor, location, force=force)
    quit(editor)


@cmd('cq')
def quit_nonzero(editor):
    """
    Quit with non zero exit status.
    """
    # Note: the try/finally in `prompt_toolkit.Interface.read_input`
    # will ensure that the render output is reset, leaving the alternate
    # screen before quitting.
    editor.application.exit()


@cmd('wa')
def write_all(editor):
    """
    Write all changed buffers
    """
    for eb in editor.window_arrangement.editor_buffers:
        if eb.location is None:
            editor.show_message(_NO_FILE_NAME)
            break
        else:
            eb.write()


@location_cmd('wqa', accepts_force=True)
def write_and_quit_all(editor, location, force=False):
    """
    Write all changed buffers and quit all.
    """
    write_all(editor)
    quit_all(editor)


@cmd('h')
@cmd('help')
def help(editor):
    """
    Show help.
    """
    editor.show_help()


@location_cmd('tabe')
@location_cmd('tabedit')
@location_cmd('tabnew')
def tab_new(editor, location):
    """
    Create new tab page.
    """
    editor.window_arrangement.create_tab(location or None)


@cmd('tabclose')
@cmd('tabc')
def tab_close(editor):
    """
    Close tab page.
    """
    editor.window_arrangement.close_tab()


@cmd('tabnext')
@cmd('tabn')
def tab_next(editor):
    """
    Go to next tab.
    """
    editor.window_arrangement.go_to_next_tab()


@cmd('tabprevious')
@cmd('tabp')
def tab_previous(editor):
    """
    Go to previous tab.
    """
    editor.window_arrangement.go_to_previous_tab()


@cmd('pwd')
def pwd(editor):
    " Print working directory. "
    directory = os.getcwd()
    editor.show_message('{}'.format(directory))


@location_cmd('cd', accepts_force=False)
def cd(editor, location):
    " Change working directory. "
    try:
        os.chdir(os.path.expanduser(location))
    except OSError as e:
        editor.show_message('{}'.format(e))


@_cmd('colorscheme')
@_cmd('colo')
def color_scheme(editor, variables):
    """
    Go to one of the open buffers.
    """
    colorscheme = variables.get('colorscheme')
    if colorscheme:
        editor.use_colorscheme(colorscheme)


@set_cmd('nu')
@set_cmd('number')
def line_numbers_show(editor):
    """ Show line numbers.  """
    editor.show_line_numbers = True


@set_cmd('nonu')
@set_cmd('nonumber')
def line_numbers_hide(editor):
    """ Hide line numbers. """
    editor.show_line_numbers = False


@set_cmd('hlsearch')
@set_cmd('hls')
def search_highlight(editor):
    """ Highlight search matches. """
    editor.highlight_search = True


@set_cmd('nohlsearch')
@set_cmd('nohls')
def search_no_highlight(editor):
    """ Don't highlight search matches. """
    editor.highlight_search = False


@set_cmd('paste')
def paste_mode(editor):
    """ Enter paste mode. """
    editor.paste_mode = True


@set_cmd('nopaste')
def paste_mode_leave(editor):
    """ Leave paste mode. """
    editor.paste_mode = False


@set_cmd('ruler')
@set_cmd('ru')
def ruler_show(editor):
    """ Show ruler. """
    editor.show_ruler = True


@set_cmd('noruler')
@set_cmd('noru')
def ruler_hide(editor):
    """ Hide ruler. """
    editor.show_ruler = False


@set_cmd('wildmenu')
@set_cmd('wmnu')
def wild_menu_show(editor):
    """ Show wildmenu. """
    editor.show_wildmenu = True


@set_cmd('nowildmenu')
@set_cmd('nowmnu')
def wild_menu_hide(editor):
    """ Hide wildmenu. """
    editor.show_wildmenu = False


@set_cmd('filetype', accepts_value=True)
@set_cmd('ft', accepts_value=True)
def filetype(editor, value):
    """
    Set filetype.
    """
    if value is None:
        editor.show_message('filetype=%s' % editor.current_editor_buffer.buffer.filetype)
    else:
        editor.current_editor_buffer.buffer.filetype = value
        window = editor.window_arrangement.active_pt_window
        window.content.lexer = DocumentLexer(editor.current_editor_buffer)

@set_cmd('autoindent')
@set_cmd('ai')
def autoindent(editor):
    """ Enable autoindent. """
    editor.current_editor_buffer.buffer.autoindent = True


@set_cmd('noautoindent')
@set_cmd('noai')
def noautoindent(editor):
    """ Disable tab expension. """
    editor.current_editor_buffer.buffer.autoindent = False


@set_cmd('expandtab')
@set_cmd('et')
def tab_expand(editor):
    """ Enable tab expension. """
    editor.current_editor_buffer.buffer.expand_tab = True


@set_cmd('noexpandtab')
@set_cmd('noet')
def tab_no_expand(editor):
    """ Disable tab expension. """
    editor.current_editor_buffer.buffer.expand_tab = False


@set_cmd('tabstop', accepts_value=True)
@set_cmd('ts', accepts_value=True)
def tab_stop(editor, value):
    """
    Set tabstop.
    """
    if value is None:
        editor.show_message('tabstop=%i' % editor.tabstop)
    else:
        try:
            value = int(value)
            if value > 0:
                editor.current_editor_buffer.buffer.tabstop = value
            else:
                editor.show_message('Argument must be positive')
        except ValueError:
            editor.show_message('Number required after =')


@set_cmd('shiftwidth', accepts_value=True)
@set_cmd('sw', accepts_value=True)
def shift_width(editor, value):
    """
    Set shiftwidth.
    """
    if value is None:
        editor.show_message('shiftwidth=%i' % editor.shiftwidth)
    else:
        try:
            value = int(value)
            if value > 0:
                editor.current_editor_buffer.buffer.shiftwidth = value
            else:
                editor.show_message('Argument must be positive')
        except ValueError:
            editor.show_message('Number required after =')


@set_cmd('scrolloff', accepts_value=True)
@set_cmd('so', accepts_value=True)
def set_scroll_offset(editor, value):
    """
    Set scroll offset.
    """
    if value is None:
        editor.show_message('scrolloff=%i' % editor.scroll_offset)
    else:
        try:
            value = int(value)
            if value >= 0:
                editor.scroll_offset = value
            else:
                editor.show_message('Argument must be positive')
        except ValueError:
            editor.show_message('Number required after =')


@set_cmd('incsearch')
@set_cmd('is')
def incsearch_enable(editor):
    """ Enable incsearch. """
    editor.incsearch = True


@set_cmd('noincsearch')
@set_cmd('nois')
def incsearch_disable(editor):
    """ Disable incsearch. """
    editor.incsearch = False


@set_cmd('ignorecase')
@set_cmd('ic')
def search_ignorecase(editor):
    """ Enable case insensitive searching. """
    editor.ignore_case = True


@set_cmd('noignorecase')
@set_cmd('noic')
def searc_no_ignorecase(editor):
    """ Disable case insensitive searching. """
    editor.ignore_case = False


@set_cmd('list')
def unprintable_show(editor):
    """ Display unprintable characters. """
    editor.display_unprintable_characters = True


@set_cmd('nolist')
def unprintable_hide(editor):
    """ Hide unprintable characters. """
    editor.display_unprintable_characters = False


@set_cmd('jedi')
def jedi_enable(editor):
    """ Enable Jedi autocompletion for Python files. """
    editor.enable_jedi = True


@set_cmd('nojedi')
def jedi_disable(editor):
    """ Disable Jedi autocompletion. """
    editor.enable_jedi = False


@set_cmd('wrapscan')
@set_cmd('ws')
def wrapscan_enable(editor):
    """ Enable search wrapscan. """
    editor.enable_wrapscan = True


@set_cmd('nowrapscan')
@set_cmd('nows')
def wrapscan_disable(editor):
    """ Disable search wrapscan. """
    editor.enable_wrapscan = False


@set_cmd('relativenumber')
@set_cmd('rnu')
def relative_number(editor):
    " Enable relative number "
    editor.relative_number = True


@set_cmd('norelativenumber')
@set_cmd('nornu')
def no_relative_number(editor):
    " Disable relative number "
    editor.relative_number = False


@set_cmd('wrap')
def enable_wrap(editor):
    " Enable line wrapping. "
    editor.wrap_lines = True


@set_cmd('nowrap')
def disable_wrap(editor):
    " disable line wrapping. "
    editor.wrap_lines = False


@set_cmd('breakindent')
@set_cmd('bri')
def enable_breakindent(editor):
    " Enable the breakindent option. "
    editor.break_indent = True


@set_cmd('nobreakindent')
@set_cmd('nobri')
def disable_breakindent(editor):
    " Enable the breakindent option. "
    editor.break_indent = False


@set_cmd('mouse')
def enable_mouse(editor):
    " Enable mouse . "
    editor.enable_mouse_support = True


@set_cmd('nomouse')
def disable_mouse(editor):
    " Disable mouse. "
    editor.enable_mouse_support = False


@set_cmd('tildeop')
@set_cmd('top')
def enable_tildeop(editor):
    " Enable tilde operator. "
    editor.application.vi_state.tilde_operator = True


@set_cmd('notildeop')
@set_cmd('notop')
def disable_tildeop(editor):
    " Disable tilde operator. "
    editor.application.vi_state.tilde_operator = False


@set_cmd('cursorline')
@set_cmd('cul')
def enable_cursorline(editor):
    " Highlight the line that contains the cursor. "
    editor.cursorline = True


@set_cmd('nocursorline')
@set_cmd('nocul')
def disable_cursorline(editor):
    " No cursorline. "
    editor.cursorline = False


@set_cmd('cursorcolumn')
@set_cmd('cuc')
def enable_cursorcolumn(editor):
    " Highlight the column that contains the cursor. "
    editor.cursorcolumn = True


@set_cmd('nocursorcolumn')
@set_cmd('nocuc')
def disable_cursorcolumn(editor):
    " No cursorcolumn. "
    editor.cursorcolumn = False


@set_cmd('colorcolumn', accepts_value=True)
@set_cmd('cc', accepts_value=True)
def set_color_column(editor, value):
    try:
        if value:
            numbers = [int(val) for val in value.split(',')]
        else:
            numbers = []
    except ValueError:
        editor.show_message(
            'Invalid value. Expecting comma separated list of integers')
    else:
        editor.colorcolumn = numbers


@set_cmd('all')
def set_all(editor):
    def handler():
        options = editor.get_current_buffer_options()
        option_strings = []
        for k in sorted(options):
            v = options[k]
            if isinstance(v, bool):
                s = f"  {k}" if v else f"no{k}"
            else:
                s = f"  {k}={v}"
            option_strings.append(s)
        print("\n".join(option_strings))
        input('\nPress ENTER to continue...')
    run_in_terminal(handler)


def _get_line_index(editor, cursor_position_row, range_start, range_end):
    if not range_start:
        assert not range_end
        range_start = range_end = cursor_position_row
    else:
        if range_start[0] == "'":
            range_start = editor.current_editor_buffer.buffer.mark[range_start[1]]
        elif range_start[0] == "$":
            range_start = editor.current_editor_buffer.buffer.document.line_count
        range_start = int(range_start) - 1
        if range_end:
            if range_end[0] == "'":
                range_end = editor.current_editor_buffer.buffer.mark[range_end[1]]
            elif range_end[0] == "$":
                range_end = editor.current_editor_buffer.buffer.document.line_count
            range_end = int(range_end) - 1
        else:
            range_end = range_start
    return range_start, range_end + 1


def substitute(editor, range_start, range_end, search, replace, flags):
    """ Substitute /search/ with /replace/ over a range of text """
    def get_transform_callback(search, replace, flags):
        SUBSTITUTE_ALL, SUBSTITUTE_ONE = 0, 1
        sub_count = SUBSTITUTE_ALL if 'g' in flags else SUBSTITUTE_ONE
        return lambda s: re.sub(search, replace, s, count=sub_count)

    search_state = editor.application.current_search_state
    buffer = editor.current_editor_buffer.buffer
    cursor_position_row = buffer.document.cursor_position_row

    # read editor state
    if not search:
        search = search_state.text

    if replace is None:
        replace = editor.last_substitute_text

    start, end = _get_line_index(editor, cursor_position_row, range_start, range_end)
    line_index_iterator = range(start, end)
    transform_callback = get_transform_callback(search, replace, flags)
    new_text = buffer.transform_lines(line_index_iterator, transform_callback)

    assert len(line_index_iterator) >= 1
    new_cursor_position_row = line_index_iterator[-1]

    # update text buffer
    buffer.document = Document(
        new_text,
        Document(new_text).translate_row_col_to_index(new_cursor_position_row, 0),
    )
    buffer.cursor_position += buffer.document.get_start_of_line_position(after_whitespace=True)
    buffer._search(search_state, include_current_position=True)

    # update editor state
    editor.last_substitute_text = replace
    search_state.text = search


def yank(editor, range_start, range_end):
    buffer = editor.current_editor_buffer.buffer
    cursor_position_row = buffer.document.cursor_position_row
    start, end = _get_line_index(editor, cursor_position_row, range_start, range_end)
    lines = buffer.document.lines

    yanked = "\n".join(lines[start: end])
    get_app().clipboard.set_data(ClipboardData(yanked, SelectionType.LINES))


def delete(editor, range_start, range_end):
    buffer = editor.current_editor_buffer.buffer
    cursor_position_row = buffer.document.cursor_position_row
    start, end = _get_line_index(editor, cursor_position_row, range_start, range_end)

    lines = buffer.document.lines

    before = "\n".join(lines[: start])
    deleted = "\n".join(lines[start: end])
    after = "\n".join(lines[end:])
    get_app().clipboard.set_data(ClipboardData(deleted, SelectionType.LINES))

    new_text = before + after
    # update text buffer
    buffer.document = Document(
        new_text,
        Document(new_text).translate_row_col_to_index(start, 0),
    )
    buffer.cursor_position += start
