pyvim
=====

An implementation of Vim in Python

Motivation
------------

The original `pyvim <https://github.com/prompt-toolkit/pyvim>`_ seems to have been written
to prove the usefulness of the `python-prompt-toolkit <https://github.com/prompt-toolkit/python-prompt-toolkit>`_ .

I am trying to modify it to a more vi/vim like editor.
It is intended to be one of the vi clones that can be used on a daily basis.


Installation
------------

Execute bellow pip command in the python virtual environment of your project.

::

    pip install git+https://github.com/nakagami/pyvim


And you can execute ``pyvim`` command.

Configuring pyvim
-----------------

It is possible to create a ``.pyvimrc`` file for a custom configuration.
Have a look at this example: `pyvimrc
<https://github.com/nakagami/pyvim/blob/master/examples/config/pyvimrc>`_


Alternatives
------------

Certainly have a look at the alternatives:

- Original Pyvim: https://github.com/prompt-toolkit/pyvim by @jonathanslenders
- Kaa: https://github.com/kaaedit/kaa by @atsuoishimoto
- Vai: https://github.com/stefanoborini/vai by @stefanoborini
- Vis: https://github.com/martanne/vis by @martanne

Thanks
------

- To original Pyvim: https://github.com/prompt-toolkit/pyvim, by Jonathan Slenders.
- To Vi Improved, by Bram Moolenaar. For the inspiration.
- To Jedi, pyflakes and the docopt Python libraries.
- To the Python wcwidth port of Jeff Quast for support of double width characters.
- To Guido van Rossum, for creating Python.
