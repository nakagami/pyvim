#!/usr/bin/env python
import os
from setuptools import setup, find_packages
import pyvim

with open(os.path.join(os.path.dirname(__file__), "README.rst")) as f:
    long_description = f.read()

classifiers = [
    "Development Status :: 4 - Beta",
    "License :: OSI Approved :: BSD License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Topic :: Text Editors",
]

setup(
    name="pyvim",
    author="Jonathan Slenders",
    maintainer="Hajime Nakagami",
    maintainer_email="nakagami@gmail.com",
    version=pyvim.__version__,
    license="BSD License",
    url="https://github.com/nakagami/pyvim",
    classifiers=classifiers,
    description="Pure Python Vi Implementation",
    long_description=long_description,
    packages=find_packages("."),
    install_requires=[
        "prompt_toolkit==3.0.51",
        "pyflakes",  # For Python error reporting.
        "jedi",  # For Python autocompletion
        "pygments",  # For the syntax highlighting.
        "docopt",  # For command line arguments.
        "charset_normalizer",  # detect encoding
    ],
    entry_points={
        "console_scripts": [
            "pyvim = pyvim.entry_points.run_pyvim:run",
        ]
    },
)
