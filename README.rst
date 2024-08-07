pyvim
=====

*An implementation of Vim in Python*

.. image :: https://github.com/nakagami/pyvim/raw/master/docs/images/welcome-screen.png

Issues, questions, wishes, comments, feedback, remarks? Please create a GitHub
issue, I appreciate it.


Installation
------------

Execute bellow pip command in the python virtual environment of your project.

::

    pip install git+https://github.com/nakagami/pyvim


And you can execute ``pyvim`` command.

In my case, I have configured ``~/.bashrc`` to switch vi between pyvim and vim as follows.

::

   exec_vi()
   {
       if [ x`which pyvim` = x ];
       then
           /usr/bin/env vim "$@"
       else
           /usr/bin/env pyvim "$@"
       fi
   }

   alias vi=exec_vi


The good things
---------------

The editor is written completely in Python. (There are no C extensions). This
makes development a lot faster. It's easy to prototype and integrate new
features.

We have already many nice things, for instance:

- Syntax highlighting of files, using the Pygments lexers.

- Horizontal and vertical splits, as well as tab pages. (Similar to Vim.)

- All of the functionality of `prompt_toolkit
  <http://github.com/prompt-toolkit/python-prompt-toolkit>`_. This includes a
  lot of Vi key bindings, it's platform independent and runs on Python 3.10+ .

- Several ``:set ...`` commands have been implemented, like ``incsearch``,
  ``number``, ``ignorecase``, ``wildmenu``, ``expandtab``, ``hlsearch``,
  ``ruler``, ``paste`` and ``tabstop``.

- Other working commands: ``vsplit``, ``tabnew``, ``only``, ``badd``, and many
  others.

- For Python source code, auto completion uses the amazing Jedi library, and
  code checking in done through Pyflakes.

- Colorschemes can be changed at runtime.

Further, when the project develops, it should also become possible to write
extensions in Python, and use Python as a scripting language. (Instead of
vimscript, for instance.)

We can also do some cool stuff. Like for instance running the editor on the
Python asyncio event loop and having other coroutines interact with the editor.


Some more screenshots
---------------------

Editing its own source code:

.. image :: https://github.com/nakagami/pyvim/raw/master/docs/images/editing-pyvim-source.png

Window layouts (horizontal and vertical splits + tab pages.)

.. image :: https://github.com/nakagami/pyvim/raw/master/docs/images/window-layout.png

Pyflakes for Python code checking and Jedi for autocompletion:

.. image :: https://github.com/nakagami/pyvim/raw/master/docs/images/pyflakes-and-jedi.png

Other colorschemes:

.. image :: https://github.com/nakagami/pyvim/raw/master/docs/images/colorschemes.png

Chinese and Japanese input (double width characters):

.. image :: https://raw.githubusercontent.com/nakagami/pyvim/master/docs/images/cjk.png?v2


Configuring pyvim
-----------------

It is possible to create a ``.pyvimrc`` file for a custom configuration.
Have a look at this example: `pyvimrc
<https://github.com/nakagami/pyvim/blob/master/examples/config/pyvimrc>`_


Limitations
-----------

Compared to Vi Improved, Pyvim is still less powerful in many aspects.

- ``prompt_toolkit`` does not (or not yet) allow buffers to have an individual
  cursor when buffers are opened in several windows. Currently, this results in
  some unexpected behaviour, when a file is displayed in two windows at the
  same time. (The cursor could be displayed in the wrong window and other
  windows will sometimes scroll along when the cursor moves.) This has to be
  fixed in the future.
- The data structure for a buffer is extremely simple. (Right now, it's just a
  Python string, and an integer for the cursor position.) This works extremely
  well for development and quickly prototyping of new features, but it comes
  with a performance penalty. Depending on the system, when a file has above a
  thousand lines and syntax highlighting is enabled, editing will become
  noticeable slower. (The bottleneck is probably the ``BufferControl`` code,
  which on every key press tries to reflow the text and calls pygments for
  highlighting. And this is Python code looping through single characters.)
- A lot of nice Vim features, like line folding, macros, etcetera are not yet
  implemented.
- Windows support is not that nice. It works, but could be improved. (I think
  most Windows users are not that interested in this project, but prove me
  wrong.)


Testing
-------

To run all tests, install pytest:

    pip install pytest

And then run from root pyvim directory:

    py.test


Why did I create Pyvim?
-----------------------

There are several reasons.

The main reason is maybe because it was a small step after I created the Python
``prompt-toolkit`` library. That is a library which is actually only a simply
pure Python readline replacement, but with some nice additions like syntax
highlighting and multiline editing. It was never intended to be a toolkit for
full-screen terminal applications, but at some point I realised that everything
we need for an editor was in there and I liked to challenge its design. So, I
started an editor and the first proof of concept was literally just a few
hundred lines of code, but it was already a working editor.

The creation of ``pyvim`` will make sure that we have a solid architecture for
``prompt-toolkit``, but it also aims to demonstrate the flexibility of the
library. When it makes sense, features of ``pyvim`` will move back to
``prompt-toolkit``, which in turn also results in a better Python REPL.
(see `ptpython <https://github.com/jonathanslenders/ptpython>`_, an alternative
REPL.)

Above all, it is really fun to create an editor.


Alternatives
------------

Certainly have a look at the alternatives:

- Kaa: https://github.com/kaaedit/kaa by @atsuoishimoto
- Vai: https://github.com/stefanoborini/vai by @stefanoborini
- Vis: https://github.com/martanne/vis by @martanne

Thanks
------

- To Vi Improved, by Bram Moolenaar. For the inspiration.
- To Jedi, pyflakes and the docopt Python libraries.
- To the Python wcwidth port of Jeff Quast for support of double width characters.
- To Guido van Rossum, for creating Python.
