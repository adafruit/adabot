# SPDX-FileCopyrightText: 2022 Alec Delaney
#
# SPDX-License-Identifier: MIT

"""

ci_status.py
============

Functionality using ``PyGithub`` to check the CI status of repos
contained within the Adafruit CircuitPython Bundle

* Author(s): Alec Delaney

"""

from typing import Optional
from github.Repository import Repository
from github.Workflow import Workflow
from github.GithubException import GithubException
from library_functions import StrPath
from iterate_libraries import (
    iter_remote_bundle_with_func,
    RemoteLibFunc_IterResult,
)


def run_gh_rest_check(
    lib_repo: Repository,
    user: Optional[str] = None,
    workflow_filename: Optional[str] = "build.yml",
) -> str:
    """Uses ``PyGithub`` to check the CI status of a repository

    :param Repository lib_repo: The repo as a github.Repository.Repository object
    :param str|None user: The user that triggered the run; if `None` is
        provided, any user is acceptable
    :param str|None workflow_filename: The filename of the workflow; if `None` is
        provided, any workflow name is acceptable; the default is `"build.yml"`
    :return: The requested runs conclusion
    :rtype: str
    """

    arg_dict = {}
    if user is not None:
        arg_dict["actor"] = user

    workflow: Workflow = lib_repo.get_workflow(workflow_filename)
    workflow_runs = workflow.get_runs(**arg_dict)
    return workflow_runs[0].conclusion


def check_build_status(
    lib_repo: Repository,
    user: Optional[str] = None,
    workflow_filename: Optional[str] = "build.yml",
    debug: bool = False,
) -> Optional[str]:
    """Uses ``PyGithub`` to check the build statuses of the Adafruit
    CircuitPython Bundle

    :param Repository lib_repo: The repo as a github.Repository.Repository object
    :param str|None user: The user that triggered the run; if `None` is
        provided, any user is acceptable
    :param str|None workflow_filename: The filename of the workflow; if `None`
        is provided, any workflow name is acceptable; the defail is `"build.yml"`
    :param bool debug: Whether debug statements should be printed to the standard
        output
    :return: The result of the workflow run, or ``None`` if it could not be
        determined
    :rtype: str|None
    """

    if debug:
        print("Checking", lib_repo.name)

    try:
        result = run_gh_rest_check(lib_repo, user, workflow_filename) == "success"
        if debug and not result:
            print("***", "Library", lib_repo.name, "failed the patch!", "***")
        return result
    except GithubException:
        if debug:
            print(
                "???",
                "Library",
                lib_repo.name,
                "workflow could not be determined",
                "???",
            )
        return None


def check_build_statuses(
    gh_token: str,
    user: Optional[str] = None,
    workflow_filename: Optional[str] = "build.yml",
    *,
    debug: bool = False,
) -> list[RemoteLibFunc_IterResult[bool]]:
    """Checks all the libraries in the Adafruit CircuitPython Bundle to get the
    latest build status with the requested information

    :param str gh_token: The Github token to be used for with the Github API
    :param str|None user: The user that triggered the run; if `None` is
        provided, any user is acceptable
    :param str|None workflow_filename: The filename of the workflow; if `None` is
        provided, any workflow name is acceptable; the defail is `"build.yml"`
    :param bool debug: Whether debug statements should be printed to
        the standard output
    :return: A list of tuples containing paired Repoistory objects and build
        statuses
    :rtype: list
    """

    args = (user, workflow_filename)
    kwargs = {"debug": debug}
    return iter_remote_bundle_with_func(gh_token, [(check_build_status, args, kwargs)])


def save_build_statuses(
    build_results: list[RemoteLibFunc_IterResult[bool]],
    failures_filepath: StrPath = "failures.txt",
) -> None:
    """Save the list of failed and/or errored libraries to files

    :param list failed_builds: The list of workflow run results after
        iterating through the libraries
    :param StrPath failures_filepath: The filename/filepath to write the list
        of failed libraries to; the default is "failures.txt"
    """

    # Get failed builds
    bad_builds = [result[0].name for result in build_results if result[1][0]]

    # Save the list of bad builds, if provided
    if bad_builds:
        with open(failures_filepath, mode="w", encoding="utf-8") as outputfile:
            for build in bad_builds:
                outputfile.write(build + "\n")
