# SPDX-FileCopyrightText: 2022 Alec Delaney
#
# SPDX-License-Identifier: MIT

"""

iterate_libraries.py
====================

Functionality for iterating through a cloned Adafruit CircuitPython
Bundle to run functions on each library

* Author(s): Alec Delaney

"""

import os
import glob
import pathlib
from collections.abc import Sequence, Iterable
from typing import TypeVar, Any, Union, List
from typing_extensions import TypeAlias
import parse
from github import Github
from github.Repository import Repository
from github.ContentFile import ContentFile
from library_functions import StrPath, LocalLibFunc, RemoteLibFunc

# Helpful type annotapython generic type aliastion definitions

PosArg = TypeVar("PosArg")
KeyArg = TypeVar("KeyArg")
RetArg = TypeVar("RetArg")

LocalLibFunc_IterInstruction: TypeAlias = tuple[
    LocalLibFunc, Sequence[PosArg], dict[str, KeyArg]
]
"""Instruction set as a tuple of a function to run on a local library,
a list of the positional arguments to be provided to it, and a
dictionary of keyword arguments to be provided to it.  You do not need
to include the libray path as an argument, as it is automatically
supplied."""

LocalLibFunc_IterResult: TypeAlias = tuple[StrPath, list[RetArg]]
"""Result of function(s) run on a library as a tuple of the path to
the local library modified and a list of the result(s) of the
function(s)"""

RemoteLibFunc_IterInstruction: TypeAlias = tuple[
    RemoteLibFunc, Sequence[PosArg], dict[str, KeyArg]
]
"""Instruction set as a tuple of a function to run on a remote library,
a list of the positional arguments to be provided to it, and a
dictionary of keyword arguments to be provided to it.  You do not need
to include the Repository object as an argument, as it is autmoatically
supplied."""

RemoteLibFunc_IterResult: TypeAlias = tuple[Repository, list[RetArg]]
"""Result of function(s) run on a library as a tuple of the name of
the remote library modified and a list of the result(s) of the
function(s)"""


# Global Variables

_BUNDLE_BRANCHES = ("drivers", "helpers")


def perform_func(
    item: Any,
    func_workflow: Union[RemoteLibFunc_IterInstruction, LocalLibFunc_IterInstruction],
) -> Union[List[RemoteLibFunc_IterResult], List[LocalLibFunc_IterResult]]:
    """
    Perform the given function
    """
    func_results = []
    for func, args, kwargs in func_workflow:
        result = func(item, *args, **kwargs)
        func_results.append(result)
    return func_results


def iter_local_bundle_with_func(
    bundle_path: StrPath,
    func_workflow: Iterable[LocalLibFunc_IterInstruction],
    *,
    local_folder: str = "",
) -> list[LocalLibFunc_IterResult]:
    """Iterate through the libraries and run a given function with the
    provided arguments

    :param StrPath bundle_path: The path to the cloned bundle
    :param Iterable func_workflow: An iterable of tuples containing pairs
        of functions and corresponding arguments; the path to each specific
        library is automatically provided to the functions, so the functions
        must account for it
    :return: A list containing tuples of pairs of each library path and a list
        with the results from each function
    :rtype: list
    """

    # Initialize list of results
    results = []

    # Keep track of all libraries iterated
    iterated = set()

    # Loop through each bundle branch
    for branch_name in _BUNDLE_BRANCHES:
        libraries_glob_path = os.path.join(bundle_path, "libraries", branch_name, "*")
        libraries_path_list = glob.glob(libraries_glob_path)

        # Enter each library in the bundle
        for library_path in libraries_path_list:
            iterated.add(os.path.split(library_path)[1].lower())
            func_results = perform_func(library_path, func_workflow)

            results.append((library_path, func_results))

    if local_folder:
        additional = {
            os.path.split(pathname)[1].lower()
            for pathname in glob.glob(os.path.join(local_folder, "*"))
        }
        diff = additional.difference(iterated)
        for unused in diff:
            unused_func_results = perform_func(unused, func_workflow)
            results.append((unused, unused_func_results))

    return results


# pylint: disable=too-many-locals
def iter_remote_bundle_with_func(
    gh_token: str,
    func_workflow: RemoteLibFunc_IterInstruction,
    *,
    local_folder: str = "",
) -> list[RemoteLibFunc_IterResult]:
    """Iterate through the remote bundle, accessing each library's git repo
    using the GitHub RESTful API (specifically using ``PyGithub``)

    :param str gh_token: A GitHub token with proper scopes
    :param Iterable func_workflow: An iterable of tuples containing pairs
        of functions and corresponding arguments; the path to each specific
        library is automatically provided to the functions, so the functions
        must account for it
    :return: A list containing tuples of pairs of each library path and a list
        with the results from each function
    :rtype: list
    """

    # Get the Github repo object
    github_client = Github(gh_token)
    bundle_repo = github_client.get_repo("adafruit/Adafruit_CircuitPython_Bundle")

    # Initialize list of results
    results = []

    # Keep track of all libraries iterated
    iterated = set()

    # Loop through each bundle branch
    for branch_name in _BUNDLE_BRANCHES:
        branch_repos_path = "/".join(("libraries", branch_name))
        branch_repos: list[ContentFile] = bundle_repo.get_contents(branch_repos_path)

        # Enter each library in the bundle
        for repo_file in branch_repos:
            repo_name_result: parse.Result = parse.search(
                "repos/adafruit/{repo_name:w}/", repo_file.git_url
            )
            repo_name: str = repo_name_result.named["repo_name"]

            repo = github_client.get_repo(f"adafruit/{repo_name}")
            iterated.add(repo_name.lower())

            func_results = perform_func(repo, func_workflow)
            results.append((repo, func_results))

    if local_folder:
        additional = {
            path.name.lower() for path in pathlib.Path(local_folder).glob("*")
        }
        diff = additional.difference(iterated)
        for unused in diff:
            unused_repo = github_client.get_repo(f"adafruit/{unused}")
            unused_func_results = perform_func(unused_repo, func_workflow)
            results.append((unused_repo, unused_func_results))

    return results
