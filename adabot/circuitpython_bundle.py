# SPDX-FileCopyrightText: 2017 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT

""" Checks each library in the CircuitPython Bundles for updates.
    If updates are found the bundle is updated, updates are pushed to the
    remote, and a new release is made.
"""
import contextlib
from datetime import date
from io import StringIO
import json
import os
import pathlib
import shlex
import subprocess

import sh
from circuitpython_build_tools.scripts.build_bundles import build_bundles
from sh.contrib import git

from adabot import github_requests as gh_reqs
from adabot.lib import common_funcs
from adabot import circuitpython_library_download_stats as dl_stats


BUNDLES = ["Adafruit_CircuitPython_Bundle", "CircuitPython_Community_Bundle"]

CONTRIBUTOR_CACHE = {}


def fetch_bundle(bundle, bundle_path):
    """Clones `bundle` to `bundle_path`"""
    if not os.path.isdir(bundle_path):
        os.makedirs(bundle_path, exist_ok=True)
        if "GITHUB_WORKSPACE" in os.environ:
            git_url = (
                "https://"
                + os.environ["ADABOT_GITHUB_ACCESS_TOKEN"]
                + "@github.com/adafruit/"
            )
            git.clone("-o", "adafruit", git_url + bundle + ".git", bundle_path)
        else:
            git.clone(
                "-o",
                "adafruit",
                "https://github.com/adafruit/" + bundle + ".git",
                bundle_path,
            )
    working_directory = os.getcwd()
    os.chdir(bundle_path)
    git.pull()
    git.submodule("init")
    git.submodule("update")
    os.chdir(working_directory)


def update_download_stats(bundle_path):
    """
    Updates the downloads stats for all the libraries
    """
    if not "Adafruit_CircuitPython_Bundle" in bundle_path:
        return False

    with open(os.path.join(bundle_path, "circuitpython_library_list.md")) as md_file:
        lib_list_full = md_file.read()

    submodules_list = common_funcs.get_bundle_submodules()
    lib_list_header = [
        "# Adafruit CircuitPython Library Download Stats",
        (
            "![Blinka On Computer](https://raw.githubusercontent.com/adafruit/"
            "Adafruit_CircuitPython_Bundle/main/assets/BlinkaComputer.png)  "
        ),
        "### Here is a listing of current Adafruit CircuitPython libraries download statistics.",
        f"**There are {len(submodules_list)} libraries available.**\n",
        "",
    ]

    submodules_stats = dl_stats.retrieve_pypi_stats(submodules_list)
    stats_lines = [
        "| Library (PyPI Package) | Downloads in the Last 7 Days |",
        "| --- | --- |",
    ]
    total_downloads = 0
    blinka_downloads = 0
    for download_stat in submodules_stats:
        if download_stat.name == "adafruit-blinka":
            blinka_downloads = download_stat.num_downloads
            continue
        repo_name_comps = download_stat.name.split("-")
        searchable_repo_name = " ".join(repo_name_comps)
        try:
            start_index = lib_list_full.lower().index(searchable_repo_name)
        except ValueError:
            continue
        printable_repo_name = lib_list_full[
            start_index : start_index + len(searchable_repo_name)
        ]
        stats_lines.append(
            f"| {printable_repo_name} ({download_stat.name}) | "
            f"{download_stat.num_downloads} downloads |"
        )
        total_downloads += download_stat.num_downloads

    lib_list_header.append(
        f"**Total PyPI library downloads in the last 7 days: {total_downloads}**  "
    )
    lib_list_header.append("")

    with open(
        os.path.join(bundle_path, "circuitpython_library_pypi_stats.md"), "w"
    ) as md_file:
        # Write headers
        md_file.write("\n".join(lib_list_header))
        md_file.write("\n")

        # Write library stats table
        for line in stats_lines:
            md_file.write(line + "\n")

        # Write Blika intro text
        md_file.write("\n")
        md_file.write("## Blinka\n")
        md_file.write("\n")
        md_file.write(
            "Blinka is our CircuitPython compatibility layer for MicroPython\n"
        )
        md_file.write("and single board computers such as the Raspberry Pi.\n")

        # Write Blinka stats table
        md_file.write("\n")
        md_file.write("| Blinka (PyPI Package) | Downloads in the Last 7 Days |\n")
        md_file.write("| --- | --- |\n")
        md_file.write(f"| Adafruit Blinka (adafruit-blinka) | {blinka_downloads} |\n")

    return True


# pylint: disable=too-many-locals
def check_lib_links_md(bundle_path):
    """Checks and updates the `circuitpython_library_list` Markdown document
    located in the Adafruit CircuitPython Bundle and Community Bundle.
    """
    bundle = None
    if "Adafruit_CircuitPython_Bundle" in bundle_path:
        bundle = "adafruit"
        listfile_name = "circuitpython_library_list.md"
    elif "CircuitPython_Community_Bundle" in bundle_path:
        bundle = "community"
        listfile_name = "circuitpython_community_auto_library_list.md"
    else:
        return []
    submodules_list = sorted(
        common_funcs.get_bundle_submodules(bundle=bundle),
        key=lambda module: module[1]["path"],
    )

    lib_count = len(submodules_list)
    # used to generate commit message by comparing new libs to current list
    try:
        with open(os.path.join(bundle_path, listfile_name), "r") as lib_list:
            read_lines = lib_list.read().splitlines()
    except OSError:
        read_lines = []

    write_drivers = []
    write_helpers = []
    updates_made = []
    for submodule in submodules_list:
        url = submodule[1]["url"]
        url_name = url[
            url.rfind("/")
            + 1 : (url.rfind(".") if url.rfind(".") > url.rfind("/") else len(url))
        ]
        pypi_name = ""
        if common_funcs.repo_is_on_pypi({"name": url_name}):
            pypi_name = " ([PyPi](https://pypi.org/project/{}))".format(
                url_name.replace("_", "-").lower()
            )
        docs_name = ""
        docs_link = common_funcs.get_docs_link(bundle_path, submodule)
        if docs_link:
            docs_name = f" \([Docs]({docs_link}))"  # pylint: disable=anomalous-backslash-in-string
        title = url_name.replace("_", " ")
        list_line = "* [{0}]({1}){2}{3}".format(title, url, pypi_name, docs_name)
        if list_line not in read_lines:
            updates_made.append(url_name)
        if "drivers" in submodule[1]["path"]:
            write_drivers.append(list_line)
        elif "helpers" in submodule[1]["path"]:
            write_helpers.append(list_line)

    lib_list_header = [
        "# Adafruit CircuitPython Libraries",
        (
            "![Blinka Reading](https://raw.githubusercontent.com/adafruit/"
            "Adafruit_CircuitPython_Bundle/main/assets/BlinkaBook.png)  "
        ),
        "Here is a listing of current Adafruit CircuitPython Libraries.  ",
        f"There are {lib_count} libraries available.\n",
        "## Drivers:\n",
    ]

    with open(os.path.join(bundle_path, listfile_name), "w") as md_file:
        md_file.write("\n".join(lib_list_header))
        for line in sorted(write_drivers):
            md_file.write(line + "\n")
        md_file.write("\n## Helpers:\n")
        for line in sorted(write_helpers):
            md_file.write(line + "\n")

    return updates_made


class Submodule:
    """Context managing class to use with git submodules."""

    def __init__(self, directory):
        self.directory = directory
        self.original_directory = os.path.abspath(os.getcwd())

    def __enter__(self):
        os.chdir(self.directory)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.original_directory)


def commit_to_tag(repo_path, commit):
    """Fetch the tag for `commit`."""
    with Submodule(repo_path):
        try:
            output = StringIO()
            git.describe("--tags", "--exact-match", commit, _out=output)
            commit = output.getvalue().strip()
        except sh.ErrorReturnCode_128:
            pass
    return commit


def repo_version():
    """The version as defined by the tag."""
    version = StringIO()
    try:
        git.describe("--tags", "--exact-match", _out=version)
    except sh.ErrorReturnCode_128:
        git.log(pretty="format:%h", n=1, _out=version)

    return version.getvalue().strip()


def repo_sha():
    """The SHA of the repo."""
    version = StringIO()
    git.log(pretty="format:%H", n=1, _out=version)
    return version.getvalue().strip()


def repo_remote_url(repo_path):
    """The URL for the remote branch."""
    with Submodule(repo_path):
        output = StringIO()
        git.remote("get-url", "origin", _out=output)
        return output.getvalue().strip()


def update_bundle(bundle_path):
    """Process all libraries in the bundle, and update their version if necessary."""

    if (
        "Adafruit_CircuitPython_Bundle" not in bundle_path
        and "CircuitPython_Community_Bundle" not in bundle_path
    ):
        raise ValueError(
            "bundle_path must be for "
            "Adafruit_CircuitPython_Bundle or CircuitPython_Community_Bundle"
        )

    working_directory = os.path.abspath(os.getcwd())
    os.chdir(bundle_path)
    git.submodule("foreach", "git", "fetch")
    # Regular release tags are 'x.x.x'. Exclude tags that are alpha or beta releases.
    # They will contain a '-' in the tag, such as '3.0.0-beta.5'.
    # --exclude must be before --tags.
    # sh fails to find the subcommand so we use subprocess.

    subprocess.run(  # pylint: disable=subprocess-run-check
        shlex.split(
            "git submodule foreach 'git checkout -q "
            "`git rev-list --exclude='*-*' --tags --max-count=1`'"
        ),
        stdout=subprocess.DEVNULL,
    )
    status = StringIO()
    git.status("--short", _out=status)
    updates = []
    release_required = False
    status = status.getvalue().strip()
    if status:
        for status_line in status.split("\n"):
            action, directory = status_line.split()
            if directory.endswith("library_list.md"):
                continue
            if action != "M" or not directory.startswith("libraries"):
                raise RuntimeError("Unsupported updates")

            # Compute the tag difference.
            diff = StringIO()
            git.diff("--submodule=log", directory, _out=diff)
            diff_lines = diff.getvalue().split("\n")
            commit_range = diff_lines[0].split()[2]
            commit_range = commit_range.strip(":").split(".")
            old_commit = commit_to_tag(directory, commit_range[0])
            new_commit = commit_to_tag(directory, commit_range[-1])
            url = repo_remote_url(directory)
            summary = "\n".join(diff_lines[1:-1])
            updates.append((url[:-4], old_commit, new_commit, summary))
            release_required = True
    os.chdir(working_directory)
    lib_list_updates = check_lib_links_md(bundle_path)
    if lib_list_updates:
        if "Adafruit_CircuitPython_Bundle" in bundle_path:
            listfile_name = "circuitpython_library_list.md"
            bundle_url = "https://github.com/adafruit/Adafruit_CircuitPython_Bundle/"
        elif "CircuitPython_Community_Bundle" in bundle_path:
            listfile_name = "circuitpython_community_auto_library_list.md"
            bundle_url = "https://github.com/adafruit/CircuitPython_Community_Bundle/"
        updates.append(
            (
                f"{bundle_url}{listfile_name}",  # pylint: disable=possibly-used-before-assignment
                "NA",
                "NA",
                "  > Added the following libraries: {}".format(
                    ", ".join(lib_list_updates)
                ),
            )
        )
        release_required = True

    return updates, release_required


def commit_updates(bundle_path, update_info):
    """Commit changes to `bundle_path` using `update_info` for the commit message."""
    working_directory = os.path.abspath(os.getcwd())
    message = ["Automated update by Adabot (adafruit/adabot@{})".format(repo_version())]
    os.chdir(bundle_path)
    for url, old_commit, new_commit, summary in update_info:
        url_parts = url.split("/")
        user, repo = url_parts[-2:]
        summary = summary.replace("#", "{}/{}#".format(user, repo))
        message.append(
            "Updating {} to {} from {}:\n{}".format(
                url, new_commit, old_commit, summary
            )
        )
    message = "\n\n".join(message)
    git.commit("-a", message=message)
    os.chdir(working_directory)


def push_updates(bundle_path):
    """Push bundle updates to the remote."""
    working_directory = os.path.abspath(os.getcwd())
    os.chdir(bundle_path)
    git.push()
    os.chdir(working_directory)


def get_contributors(repo, commit_range):
    """Get contributors to `repo` for the `commit_range`."""
    output = StringIO()
    try:
        git.log("--pretty=tformat:%H,%ae,%ce", commit_range, _out=output)
    except sh.ErrorReturnCode_128:
        print("Skipping contributors for:", repo)
    output = output.getvalue().strip()
    contributors = {}
    if not output:
        return contributors
    for log_line in output.split("\n"):
        sha, author_email, committer_email = log_line.split(",")
        author = CONTRIBUTOR_CACHE.get("github_username:" + author_email, None)
        committer = CONTRIBUTOR_CACHE.get("github_username:" + committer_email, None)
        if not author or not committer:
            github_commit_info = gh_reqs.get("/repos/" + repo + "/commits/" + sha)
            github_commit_info = github_commit_info.json()
            if github_commit_info["author"]:
                author = github_commit_info["author"]["login"]
                CONTRIBUTOR_CACHE["github_username:" + author_email] = author
            if github_commit_info["committer"]:
                committer = github_commit_info["committer"]["login"]
                CONTRIBUTOR_CACHE["github_username:" + committer_email] = committer

        if committer_email == "noreply@github.com":
            committer = None
        if author and author not in contributors:
            contributors[author] = 0
        if committer and committer not in contributors:
            contributors[committer] = 0
        if author:
            contributors[author] += 1
        if committer and committer != author:
            contributors[committer] += 1
    return contributors


def repo_name(url):
    """Strips off .git and splits on /"""
    if url.endswith(".git"):
        url = url[:-4]
    url = url.split("/")
    return url[-2] + "/" + url[-1]


# TODO: turn `master_list` into a set()?
def add_contributors(master_list, additions):
    """Adds contributors to `master_list` if not already in the list."""
    for contributor in additions:
        if contributor not in master_list:
            master_list[contributor] = 0
        master_list[contributor] += additions[contributor]


def test_bundle_build(bundle_dir):
    """
    Attempts to build the bundle at the given location.
    Raises system exit status 0 if successful.
    Raises system exit status >0 if failed to build.
    """
    with contextlib.chdir(bundle_dir):
        build_bundles(
            [
                "--filename_prefix",
                "test-build-bundle",
                "--library_location",
                "libraries",
                "--library_depth",
                "2",
            ],
            standalone_mode=False,
        )


# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def new_release(bundle, bundle_path):
    """Creates a new release for `bundle`."""
    working_directory = os.path.abspath(os.getcwd())
    os.chdir(bundle_path)
    print(bundle)
    current_release = gh_reqs.get("/repos/adafruit/{}/releases/latest".format(bundle))
    last_tag = current_release.json()["tag_name"]
    contributors = get_contributors("adafruit/" + bundle, last_tag + "..")
    added_submodules = []
    updated_submodules = []
    repo_links = {}

    output = StringIO()
    git.diff("--submodule=short", last_tag + "..", _out=output)
    output = output.getvalue().strip()
    if not output:
        print("Everything is already released.")
        return
    current_submodule = None
    current_index = None
    # pylint: disable=no-else-continue
    for line in output.split("\n"):
        if line.startswith("diff"):
            current_submodule = line.split()[-1][len("b/") :]
            continue
        elif "index" in line:
            current_index = line
            continue
        elif not line.startswith("+Subproject"):
            continue

        # We have a candidate submodule change.
        directory = current_submodule
        commit_range = current_index.split()[1]
        library_name = directory.split("/")[-1]
        if commit_range.startswith("0000000"):
            added_submodules.append(library_name)
            commit_range = commit_range.split(".")[-1]
        elif commit_range.endswith("0000000"):
            # For now, skip documenting deleted modules.
            continue
        else:
            updated_submodules.append(library_name)

        repo_url = repo_remote_url(directory)

        new_commit = commit_range.split(".")[-1]
        release_tag = commit_to_tag(directory, new_commit)
        with Submodule(directory):
            submodule_contributors = get_contributors(repo_name(repo_url), commit_range)
            add_contributors(contributors, submodule_contributors)
        repo_links[library_name] = repo_url[:-4] + "/releases/" + release_tag

    release_description = []
    if added_submodules:
        additions = []
        for library in added_submodules:
            additions.append("[{}]({})".format(library, repo_links[library]))
        release_description.append("New libraries: " + ", ".join(additions))

    if updated_submodules:
        updates = []
        for library in updated_submodules:
            updates.append("[{}]({})".format(library, repo_links[library]))
        release_description.append("Updated libraries: " + ", ".join(updates))

    release_description.append("")

    contributors = sorted(contributors, key=contributors.__getitem__, reverse=True)
    contributors = ["@" + x for x in contributors]

    release_description.append(
        "As always, thank you to all of our contributors: " + ", ".join(contributors)
    )

    release_description.append("\n--------------------------\n")

    release_description.append(
        "The libraries in each release are compiled for all recent major versions of CircuitPython."
        " Please download the one that matches the major version of your CircuitPython. For example"
        ", if you are running 9.1.1 you should download the `9.x` bundle.\n"
    )

    release_description.append(
        "To install, simply download the matching zip file, unzip it, and selectively copy the"
        " libraries you would like to install into the lib folder on your CIRCUITPY drive. This is"
        " especially important for non-express boards with limited flash, such as the"
        " [Trinket M0](https://www.adafruit.com/product/3500),"
        " [Gemma M0](https://www.adafruit.com/product/3501) and"
        " [Feather M0 Basic](https://www.adafruit.com/product/2772).\n"
    )

    release_description.append(
        "To automate the use of bundles, including the Adafruit CircuitPython Bundle"
        " and the Community Bundle, install [circup](https://pypi.org/project/circup/)"
        " using pip or pipx."
        " This command-line tool allows you to install packages from the bundle to your CIRCUITPY"
        " drive without manually downloading anything.\n"
    )

    release_description.append(
        "To download the libraries as Python source code, use the link containing 'bundle-py'."
        " Due to github's technical limitations, the 'Source code (zip)' and 'Source code (tar.gz')"
        " links do not contain the library source code and cannot be hidden by project admins."
    )

    release = {
        "tag_name": "{0:%Y%m%d}".format(date.today()),
        "target_commitish": repo_sha(),
        "name": "{0:%B} {0:%d}, {0:%Y} auto-release".format(date.today()),
        "body": "\n".join(release_description),
        "draft": False,
        "prerelease": False,
    }

    print("Releasing {}".format(release["tag_name"]))
    print(release["body"])
    response = gh_reqs.post("/repos/adafruit/" + bundle + "/releases", json=release)
    if not response.ok:
        print("Failed to create release")
        print(release)
        print(response.request.url)
        print(response.text)

    os.chdir(working_directory)


if __name__ == "__main__":
    contributor_cache_fn = pathlib.Path("contributors.json").resolve()
    if contributor_cache_fn.exists():
        CONTRIBUTOR_CACHE = json.loads(contributor_cache_fn.read_text())

    bundles_dir = os.path.abspath(".bundles")
    if "GITHUB_WORKSPACE" in os.environ:
        git.config("--global", "user.name", "adabot")
        git.config("--global", "user.email", os.environ["ADABOT_EMAIL"])
    for cp_bundle in BUNDLES:
        bundle_dir = os.path.join(bundles_dir, cp_bundle)
        try:
            fetch_bundle(cp_bundle, bundle_dir)
            updates, release_required = update_bundle(bundle_dir)

            # test bundle build and stop if it does not succeed
            try:
                test_bundle_build(bundle_dir)
            except SystemExit as e:
                if e.code != 0:
                    raise RuntimeError("Test Build of Bundle Failed") from e
            if release_required:
                commit_updates(bundle_dir, updates)
                push_updates(bundle_dir)
            new_release(cp_bundle, bundle_dir)
        except RuntimeError as e:
            print("Failed to update and release:", cp_bundle)
            print(e)
            raise e
        finally:
            contributor_cache_fn.write_text(json.dumps(CONTRIBUTOR_CACHE))
