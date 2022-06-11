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

git_functionality.py
====================

Functionality for using GitPython to fetch, pull, commit, push, etc. to
cloned repos and their remotes

* Author(s): Alec Delaney

"""

import functools
from typing import Any
import git
import git.repo
import git.index.base
from tools.library_functions import StrPath


def _get_repo_and_remote(
    lib_path: StrPath, remote_name: str = "origin"
) -> tuple[git.repo.Repo, git.Remote]:
    """
    Get the repo and remote objects

    :param StrPath lib_path: The path to the repo
    :param str remote_name: (optional) The name of the remote,
        default is ``origin``
    :return: The repo and remote objects
    :rtype: tuple
    """

    # Create the repo and remote objects
    repo = git.repo.Repo(lib_path)
    remote = repo.remote(remote_name)

    return repo, remote


def sync_and_checkout(
    lib_path: StrPath, remote_name: str = "origin", branch_name: str = "main"
) -> None:
    """
    Update the repo, and ensure it is on the given branch using a
    forced checkout

    :param StrPath lib_path: The path to the repo
    :param str remote_name: The remote name to fetch and pull,
        default is ``origin``
    :param str branch_name: The branch name to checkout, default
        is ``main``
    """

    # Create the repo and remote objects
    repo, remote = _get_repo_and_remote(lib_path, remote_name)

    # Fetch from the remote
    remote.fetch()

    # Checkout and pull to the given branchb
    # if repo.active_branch != branch_name:
    branch: git.Head = getattr(repo.heads, branch_name)
    branch.checkout(force=True)
    remote.pull()


def push_changes(lib_path: StrPath, remote_name: str = "origin") -> None:
    """
    Pushes any changes made to the repo to the given remote

    :param StrPath lib_path: The path to the repo
    :param str remote_name: (optional) The name of remote, default
        is ``main``
    """

    # Create the repo and remote objects
    _, remote = _get_repo_and_remote(lib_path, remote_name)

    # Push changes
    remote.push()


def commit_changes(
    lib_path: StrPath,
    message: str,
    remote_name: str = "origin",
    skip_hooks: bool = True,
) -> None:
    """
    Stage all files and commit them

    :param StrPath lib_path: The path to the repo
    :param str message: The commit message
    :param str remote_name: (optional) The name of the remote,
        default is ``origin``
    :param bool skip_hooks: (optional) Whether commit hooks should be
        skipped; default is True
    """

    # Create the repo and remote objects
    repo, _ = _get_repo_and_remote(lib_path, remote_name)

    # Add all the files and commit them
    index_file = git.index.base.IndexFile(repo)
    index_file.add("*")
    index_file.commit(message, skip_hooks=skip_hooks)


def sync_commit_push(
    message: str,
    *,
    remote_name: str = "origin",
    branch_name: str = "main",
    skip_hooks: bool = True
):
    """
    Decorator for automatically fetching, pulling, and pushing changes
    for a library function

    :param str message: The commit message
    :param str remote_name: (optional) The name of the remote, default
        is ``origin``
    :param str branch_name: (optional) The name of the branch, default
        is ``main``
    :param bool skip_hooks: (optional) Whether to skip the commit hooks,
        default is ``True``
    """

    def decorator_sync_commit_push(func):

        functools.wraps(func)

        def wrapper_sync_commit_push(lib_path: StrPath, *args, **kwargs) -> Any:

            # Fetch and pull to repo
            sync_and_checkout(lib_path, remote_name, branch_name)

            # Run fucntion
            result = func(lib_path, *args, **kwargs)

            # Commit and push changes
            commit_changes(lib_path, message, remote_name, skip_hooks)
            push_changes(lib_path, remote_name)

            # Return the function result(s)
            return result

        return wrapper_sync_commit_push

    return decorator_sync_commit_push
