"""
`rc_file`s are configuration files.

A pyvim configuration file is just a Python file that contains a global
`configure` function. During startup, that function will be called with the
editor instance as an argument.
"""

from .editor import Editor

import os
import traceback

__all__ = ("run_rc_file",)


def _press_enter_to_continue():
    """Wait for the user to press enter."""
    input("\nPress ENTER to continue...")


def run_rc_file(editor, rc_file):
    """
    Run rc file.
    """
    assert isinstance(editor, Editor)
    assert isinstance(rc_file, str)

    # Expand tildes.
    rc_file = os.path.expanduser(rc_file)

    # Check whether this file exists.
    if not os.path.exists(rc_file):
        print("Impossible to read %r" % rc_file)
        _press_enter_to_continue()
        return

    # Run the rc file in an empty namespace.
    try:
        namespace = {}

        with open(rc_file, "r") as f:
            code = compile(f.read(), rc_file, "exec")
            exec(code, namespace, namespace)

        # Now we should have a 'configure' method in this namespace. We call this
        # method with editor as an argument.
        if "configure" in namespace:
            namespace["configure"](editor)

    except Exception:
        # Handle possible exceptions in rc file.
        traceback.print_exc()
        _press_enter_to_continue()
