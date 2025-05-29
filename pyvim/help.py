HELP_TEXT = """\
PyVim Help
==========

PyVim is a Pure Python Vim Clone.

Commands like shell
------------------------------

- :cd                       Change directory
- :pwd                      Print working directory

Commands for tab and window
------------------------------

- :tabe :tabedit :tabnew    Create new tab page
- :tabclose :tabc           Close tab page
- :tabnext :tabn            Net tab
- :tabprevious :tabp        Previsou tab
- :sp :split                Split window horizontally
- :vsp :vsplit              Split window vertically
- :new                      Create new buffer
- :vnew                     Create new buffer, splitting vertically
- :only                     Keep only the current window
- :hide                     Hide the current window

Keybinds for tab and window
------------------------------

- Ctrl+g t                  Next tab page
- Ctrl+g T                  Previous tab page
- Ctrl+w Ctrl+w             Next window
- Ctrl+w n                  Split horizontaly
- Ctrl+w v                  Split vertically

Keybinds in autocompletion
------------------------------

When editing Python with Jedi enabled, an autocomplete window appears and follows these key bindings

- Ctrl+n                    Select next candidate
- Ctrl+p                    Select previsous candidate
- Tab                       Close autocompletion window
- Ctrl+c                    Cancel completion and close autocompletion window

Thanks to
---------------

- Pyflakes: the tool for checking Python source files for errors.
- Jedi: the Python autocompletion library.
- Pygments: Python syntax highlighter.
- prompt_toolkit: the terminal UI toolkit."""
