pyvim
=====

*An implementation of Vim in Python*

The original `pyvim <https://github.com/prompt-toolkit/pyvim>`_ seems to have been written to prove the usefulness of the prompt toolkit.

I am trying to fork pyvim into a more vi/vim-like editor.

.. image :: https://github.com/nakagami/pyvim/raw/master/docs/images/welcome-screen.png


Installation
------------

Execute bellow pip command in the python virtual environment of your project.

::

    pip install git+https://github.com/nakagami/pyvim


And you can execute ``pyvim`` command.

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


Certainly have a look at the alternatives:

- Original Pyvim: https://github.com/prompt-toolkit/pyvim by @jonathanslenders
- Kaa: https://github.com/kaaedit/kaa by @atsuoishimoto
- Vai: https://github.com/stefanoborini/vai by @stefanoborini
- Vis: https://github.com/martanne/vis by @martanne

Thanks
------

- To Vi Improved, by Bram Moolenaar. For the inspiration.
- To Jedi, pyflakes and the docopt Python libraries.
- To the Python wcwidth port of Jeff Quast for support of double width characters.
- To Guido van Rossum, for creating Python.
