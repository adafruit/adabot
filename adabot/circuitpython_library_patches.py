# SPDX-FileCopyrightText: 2019 Michael Schroeder
#
# SPDX-License-Identifier: MIT

"""Adabot utility for applying patches to all CircuitPython Libraries."""

import argparse
import os
import shutil
import sys

import requests
import sh
from sh.contrib import git

from adabot import REQUESTS_TIMEOUT
from adabot.lib import common_funcs


working_directory = os.path.abspath(os.getcwd())
lib_directory = working_directory + "/.libraries/"
patch_directory = working_directory + "/patches/"
repos = []
check_errors = []
apply_errors = []
stats = []

"""
Setup the command line argument parsing object.
"""
cli_parser = argparse.ArgumentParser(
    description="Apply patches to any common file(s) in"
    " all Adafruit CircuitPython Libraries."
)
cli_parser.add_argument(
    "-l", "--list", help="Lists the available patches to run.", action="store_true"
)
cli_parser.add_argument(
    "-p",
    help="Runs only the single patch referenced.",
    metavar="<PATCH FILENAME>",
    dest="patch",
)
cli_parser.add_argument(
    "-f",
    help="Adds the referenced FLAGS to the git.am call."
    " Only available when using '-p'. Enclose flags in brackets '[]'."
    " Multiple flags can be passed. NOTE: '--signoff' is already used "
    " used by default, and will be ignored. EXAMPLE: -f [-C0] -f [-s]",
    metavar="FLAGS",
    action="append",
    dest="flags",
    type=str,
)
cli_parser.add_argument(
    "--use-apply",
    help="Forces use of 'git apply' instead of 'git am'."
    " This is necessary when needing to use 'apply' flags not available"
    " to 'am' (e.g. '--unidiff-zero'). Only available when using '-p'.",
    action="store_true",
    dest="use_apply",
)
cli_parser.add_argument(
    "--dry-run",
    help="Apply patches locally but do not commit or push them.",
    action="store_true",
    dest="dry_run",
)
cli_parser.add_argument(
    "--commit-changes",
    help="Commit any local changes in each previously cloned library"
    " using the [PATCH] message from the referenced patch (requires '-p')."
    " Does not clone, apply, or push. Intended to be run after '--dry-run'"
    " and any manual edits.",
    action="store_true",
    dest="commit_changes",
)
cli_parser.add_argument(
    "--push-changes",
    help="Push existing commits in each previously cloned library."
    " Does not clone, apply, or commit. Intended to be run after"
    " '--commit-changes'.",
    action="store_true",
    dest="push_changes",
)
cli_parser.add_argument(
    "--local",
    help="Force use of local patches. This skips verification"
    " of patch files in the adabot GitHub repository. MUST use '--dry-run'"
    " with this argument; this guards against applying unapproved patches.",
    action="store_true",
    dest="run_local",
)


def get_repo_list():
    """Uses adabot.circuitpython_libraries module to get a list of
    CircuitPython repositories. Filters the list down to adafruit
    owned/sponsored CircuitPython libraries.
    """
    repo_list = []
    get_repos = common_funcs.list_repos()
    for repo in get_repos:
        if not (
            repo["owner"]["login"] == "adafruit"
            and repo["name"].startswith("Adafruit_CircuitPython")
        ):
            continue
        repo_list.append(dict(name=repo["name"], url=repo["clone_url"]))

    return repo_list


def get_patches(run_local):
    """Returns the list of patch files located in the adabot/patches
    directory.
    """
    return_list = []
    if not run_local:
        contents = requests.get(
            "https://api.github.com/repos/adafruit/adabot/contents/patches",
            timeout=REQUESTS_TIMEOUT
        )
        if contents.ok:
            for patch in contents.json():
                patch_name = patch["name"]
                return_list.append(patch_name)
    else:
        contents = os.listdir(patch_directory)
        for file in contents:
            if file.endswith(".patch"):
                return_list.append(file)

    return return_list

# pylint: disable=too-many-arguments
def apply_patch(
    repo_directory,
    patch_filepath,
    repo,
    patch,
    flags,
    use_apply,
    dry_run=False,
):
    """Apply the `patch` in `patch_filepath` to the `repo` in
    `repo_directory` using git am or git apply. When `dry_run` is
    true the patch is applied to the working tree only, not committed
    or pushed.

    When `use_apply` is true, the `--apply` flag is automatically added
    to ensure that any passed flags that turn off apply (e.g. `--check`)
    are overridden.
    """
    if not os.getcwd() == repo_directory:
        os.chdir(repo_directory)

    if not use_apply and not dry_run:
        try:
            git.am(flags, patch_filepath)
        except sh.ErrorReturnCode as err:
            apply_errors.append(
                dict(repo_name=repo, patch_name=patch, error=err.stderr)
            )
            return False
    else:
        apply_flags = ["--apply"]
        for flag in flags:
            if not flag == "--signoff":
                apply_flags.append(flag)
        try:
            git.apply(apply_flags, patch_filepath)
        except sh.ErrorReturnCode as err:
            apply_errors.append(
                dict(repo_name=repo, patch_name=patch, error=err.stderr)
            )
            return False

        if not dry_run:
            with open(patch_filepath) as patchfile:
                for line in patchfile:
                    if "[PATCH]" in line:
                        message = '"' + line[(line.find("]") + 2) :] + '"'
                        break
            try:
                git.commit("-a", "-m", message)
            except sh.ErrorReturnCode as err:
                apply_errors.append(
                    dict(repo_name=repo, patch_name=patch, error=err.stderr)
                )
                return False

    if dry_run:
        return True

    try:
        git.push()
    except sh.ErrorReturnCode as err:
        apply_errors.append(dict(repo_name=repo, patch_name=patch, error=err.stderr))
        return False
    return True


def commit_local_changes(repo_directory, patch_filepath, repo_name, patch):
    """Commit any local changes in `repo_directory` using the [PATCH]
    message from `patch_filepath`. Mirrors the commit logic used by
    `apply_patch` for the `--use-apply` path.
    """
    if not os.getcwd() == repo_directory:
        os.chdir(repo_directory)

    # Skip if there is nothing to commit.
    status = git.status("--porcelain").stdout.strip()
    if not status:
        return None

    message = None
    with open(patch_filepath) as patchfile:
        for line in patchfile:
            if "[PATCH]" in line:
                message = '"' + line[(line.find("]") + 2) :] + '"'
                break
    if message is None:
        apply_errors.append(
            dict(
                repo_name=repo_name,
                patch_name=patch,
                error=b"No [PATCH] line found in patch file.",
            )
        )
        return False

    try:
        git.commit("-a", "-m", message)
    except sh.ErrorReturnCode as err:
        apply_errors.append(
            dict(repo_name=repo_name, patch_name=patch, error=err.stderr)
        )
        return False
    return True


def push_local_commits(repo_directory, repo_name):
    """Push existing commits in `repo_directory`. Mirrors the push
    logic used by `apply_patch`.
    """
    if not os.getcwd() == repo_directory:
        os.chdir(repo_directory)
    try:
        git.push()
    except sh.ErrorReturnCode as err:
        apply_errors.append(
            dict(repo_name=repo_name, patch_name="", error=err.stderr)
        )
        return False
    return True


# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def check_patches(repo, patches, flags, use_apply, dry_run):
    """Gather a list of patches from the `adabot/patches` directory
    on the adabot repo. Clone the `repo` and run git apply --check
    to test wether it requires any of the gathered patches.

    When `use_apply` is true, any flags except `--apply` are passed
    through to the check call. This ensures that the check call is
    representative of the actual apply call.
    """
    applied = 0
    skipped = 0
    failed = 0

    repo_directory = lib_directory + repo["name"]

    for patch in patches:
        try:
            os.chdir(lib_directory)
        except FileNotFoundError:
            os.mkdir(lib_directory)
            os.chdir(lib_directory)

        try:
            git.clone(repo["url"])
        except sh.ErrorReturnCode_128 as err:
            if b"already exists" in err.stderr:
                pass
            else:
                raise RuntimeError(err.stderr) from None
        os.chdir(repo_directory)

        patch_filepath = patch_directory + patch

        try:
            check_flags = ["--check"]
            if use_apply:
                for flag in flags:
                    if not flag in ("--apply", "--signoff"):
                        check_flags.append(flag)
            git.apply(check_flags, patch_filepath)
            run_apply = True
        except sh.ErrorReturnCode_1 as err:
            run_apply = False
            if b"error" not in err.stderr or b"patch does not apply" in err.stderr:
                parse_err = err.stderr.decode()
                parse_err = parse_err[parse_err.rfind(":") + 1 : -1]
                print("   . Skipping {}:{}".format(repo["name"], parse_err))
                skipped += 1
            else:
                failed += 1
                error_str = str(err.stderr, encoding="utf-8").replace("\n", " ")
                error_start = error_str.rfind("error:") + 7
                check_errors.append(
                    dict(
                        repo_name=repo["name"],
                        patch_name=patch,
                        error=error_str[error_start:],
                    )
                )

        except sh.ErrorReturnCode as err:
            run_apply = False
            failed += 1
            error_str = str(err.stderr, encoding="utf-8").replace("\n", " ")
            error_start = error_str.rfind("error:") + 7
            check_errors.append(
                dict(
                    repo_name=repo["name"],
                    patch_name=patch,
                    error=error_str[error_start:],
                )
            )

        if run_apply:
            result = apply_patch(
                repo_directory,
                patch_filepath,
                repo["name"],
                patch,
                flags,
                use_apply,
                dry_run,
            )
            if result:
                applied += 1
            else:
                failed += 1

    return [applied, skipped, failed]


if __name__ == "__main__":
    cli_args = cli_parser.parse_args()

    mode_flags = [cli_args.dry_run, cli_args.commit_changes, cli_args.push_changes]
    if sum(bool(m) for m in mode_flags) > 1:
        raise RuntimeError(
            "'--dry-run', '--commit-changes', and '--push-changes' are"
            " mutually exclusive."
        )

    if cli_args.run_local:
        if cli_args.dry_run or cli_args.commit_changes or cli_args.list:
            pass
        else:
            raise RuntimeError(
                "'--local' can only be used in conjunction with"
                " '--dry-run', '--commit-changes', or '--list'."
            )

    run_patches = get_patches(cli_args.run_local)
    cmd_flags = ["--signoff"]

    if cli_args.list:
        print("Available Patches:", run_patches)
        sys.exit()
    if cli_args.patch:
        if not cli_args.patch in run_patches:
            raise ValueError(
                "'{}' is not an available patchfile.".format(cli_args.patch)
            )
        run_patches = [cli_args.patch]
    if cli_args.commit_changes and not cli_args.patch:
        raise RuntimeError(
            "'--commit-changes' requires '-p <PATCH FILENAME>' so the"
            " commit message can be derived from the patch."
        )
    if cli_args.flags is not None:
        if not cli_args.patch:
            raise RuntimeError(
                "Must be used with a single patch. See help (-h) for usage."
            )
        if "[-i]" in cli_args.flags:
            raise ValueError("Interactive Mode flag not allowed.")
        for flag_arg in cli_args.flags:
            if not flag_arg == "[--signoff]":
                cmd_flags.append(flag_arg.strip("[]"))
    if cli_args.use_apply:
        if not cli_args.patch:
            raise RuntimeError(
                "Must be used with a single patch. See help (-h) for usage."
            )

    print(".... Beginning Patch Updates ....")
    print(".... Working directory:", working_directory)
    print(".... Library directory:", lib_directory)
    print(".... Patches directory:", patch_directory)

    check_errors = []
    apply_errors = []
    stats = [0, 0, 0]

    # --commit-changes and --push-changes operate on the libraries that
    # were previously cloned (e.g. by a prior '--dry-run' invocation),
    # so do not wipe or re-clone anything.
    if cli_args.commit_changes or cli_args.push_changes:
        try:
            local_libs = sorted(os.listdir(path=lib_directory))
        except FileNotFoundError:
            local_libs = []

        if cli_args.commit_changes:
            patch = cli_args.patch
            patch_filepath = patch_directory + patch
            print(
                ".... Committing local changes in",
                len(local_libs),
                "Repos ....",
            )
            for lib in local_libs:
                repo_directory = lib_directory + lib
                if not os.path.isdir(repo_directory):
                    continue
                result = commit_local_changes(
                    repo_directory, patch_filepath, lib, patch
                )
                if result is True:
                    stats[0] += 1
                elif result is None:
                    stats[1] += 1
                else:
                    stats[2] += 1
        else:  # push_changes
            print(".... Pushing commits in", len(local_libs), "Repos ....")
            for lib in local_libs:
                repo_directory = lib_directory + lib
                if not os.path.isdir(repo_directory):
                    continue
                result = push_local_commits(repo_directory, lib)
                if result:
                    stats[0] += 1
                else:
                    stats[2] += 1
    else:
        print(".... Deleting any previously cloned libraries")
        try:
            libs = os.listdir(path=lib_directory)
            for lib in libs:
                shutil.rmtree(lib_directory + lib)
        except FileNotFoundError:
            pass

        repos = get_repo_list()
        print(".... Running Patch Checks On", len(repos), "Repos ....")

        for repository in repos:
            results = check_patches(
                repository,
                run_patches,
                cmd_flags,
                cli_args.use_apply,
                cli_args.dry_run,
            )
            for k in range(3):
                stats[k] += results[k]

    print(".... Patch Updates Completed ....")
    print(".... Patches Applied:", stats[0])
    print(".... Patches Skipped:", stats[1])
    print(".... Patches Failed:", stats[2], "\n")
    print(".... Patch Check Failure Report ....")
    if len(check_errors) > 0:
        for error in check_errors:
            print(
                ">> Repo: {0}\tPatch: {1}\n   Error: {2}".format(
                    error["repo_name"], error["patch_name"], error["error"]
                )
            )
    else:
        print("No Failures")
    print("\n")
    print(".... Patch Apply Failure Report ....")
    if len(apply_errors) > 0:
        for error in apply_errors:
            print(
                ">> Repo: {0}\tPatch: {1}\n   Error: {2}".format(
                    error["repo_name"], error["patch_name"], error["error"]
                )
            )
    else:
        print("No Failures")
