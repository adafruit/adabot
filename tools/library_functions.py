# The MIT License (MIT)
#
# Copyright (c) 2022 Eva Herrada
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""

lib_funcs.py
============

Library-specific functionalities to aid in developing patches

* Author(s): Alec Delaney

"""

import os
import functools
from collections.abc import Sequence
from typing import Protocol, Any, Union
from typing_extensions import TypeAlias
from github.Repository import Repository

# Helpful type annotation for path-like strings
StrPath: TypeAlias = Union[str, os.PathLike[str]]
"""Path or path-like strings"""

# pylint: disable=too-few-public-methods
class LocalLibFunc(Protocol):
    """Typing protocol for methods (or callables) that take the following
    parameters:

    - (StrPath) The path to a specific Adafruit library
    - (Sequence[Any]) A list of any positional arguments
    - (Dict[str, Any]) A dict of any keyword arguments
    """

    def __call__(
        self, lib_path: StrPath, *args: Sequence[Any], **kwargs: dict[str, Any]
    ) -> Any:
        ...


# pylint: disable=too-few-public-methods
class RemoteLibFunc(Protocol):
    """Typing protocol for methods (or callables) that take the following
    parameters:

    - (Repository) The repo as a github.Repository.Repository object
    - (Sequence[Any]) A list of any positional arguments
    - (Dict[str, Any]) A dict of any keyword arguments
    """

    def __call__(
        self, lib_repo: Repository, *args: Sequence[Any], **kwargs: dict[str, Any]
    ) -> Any:
        ...


def in_lib_path(func: LocalLibFunc) -> LocalLibFunc:
    """Decorator for automating temporarily entering a function's
    library directory

    :param LibraryFunc func: The library function to decorate
    """

    @functools.wraps(func)
    def wrapper_use_lib_path(lib_path: StrPath, *args, **kwargs) -> Any:

        # Get the current directory
        current_path = os.getcwd()

        # Enter the library directory for the duration of executing the function
        os.chdir(lib_path)
        result = func(lib_path, *args, **kwargs)
        os.chdir(current_path)

        # Return the result of the function
        return result

    return wrapper_use_lib_path
