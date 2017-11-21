# The MIT License (MIT)
#
# Copyright (c) 2017 Scott Shawcroft for Adafruit Industries
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

from adabot import requests
import os
import subprocess
import shlex
from io import StringIO

import sh
from sh.contrib import git

bundles = ["Adafruit_CircuitPython_Bundle", "CircuitPython_Community_Bundle"]

def fetch_bundle(bundle, directory):
    if not os.path.isdir(bundle_path):
        os.makedirs(directory, exist_ok=True)
        git.clone("-o", "adafruit", "https://github.com/adafruit/" + bundle + ".git", bundle_path)
    working_directory = os.getcwd()
    os.chdir(bundle_path)
    git.pull()
    git.submodule("init")
    git.submodule("update")
    os.chdir(working_directory)


class Submodule:
    def __init__(self, directory):
        self.directory = directory

    def __enter__(self):
        self.original_directory = os.path.abspath(os.getcwd())
        os.chdir(self.directory)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.original_directory)


def commit_to_tag(repo_path, commit):
    with Submodule(repo_path):
        try:
            output = StringIO()
            git.describe("--tags", "--exact-match", commit, _out=output)
            commit = output.getvalue().strip()
        except sh.ErrorReturnCode_128:
            pass
    return commit

def repo_version():
    version = StringIO()
    try:
        git.describe("--tags", "--exact-match", _out=version)
    except sh.ErrorReturnCode_128:
        git.log(pretty="format:%h", n=1, _out=version)

    return version.getvalue().strip()


def repo_remote_url(repo_path):
    with Submodule(repo_path):
        output = StringIO()
        git.remote("get-url", "origin", _out=output)
        return output.getvalue().strip()

def update_bundle(bundle_path):
    working_directory = os.path.abspath(os.getcwd())
    os.chdir(bundle_path)
    git.submodule("foreach", "git", "fetch")
    # sh fails to find the subcommand so we use subprocess.
    subprocess.run(shlex.split("git submodule foreach 'git checkout -q `git rev-list --tags --max-count=1`'"), stdout=subprocess.DEVNULL)

    # Don't update circuitpython, its going away soon.
    git.submodule("update", "circuitpython")

    status = StringIO()
    result = git.status("--short", _out=status)
    updates = []
    for status_line in status.getvalue().strip().split("\n"):
        action, directory = status_line.split()
        if action != "M" or not directory.startswith("libraries"):
            RuntimeError("Unsupported updates")

        # Compute the tag difference.
        diff = StringIO()
        result = git.diff("--submodule=log", directory, _out=diff)
        diff_lines = diff.getvalue().split("\n")
        commit_range = diff_lines[0].split()[2]
        commit_range = commit_range.strip(":").split(".")
        old_commit = commit_to_tag(directory, commit_range[0])
        new_commit = commit_to_tag(directory, commit_range[-1])
        url = repo_remote_url(directory)
        summary = "\n".join(diff_lines[1:-1])
        updates.append((url[:-4], old_commit, new_commit, summary))
    os.chdir(working_directory)
    return updates

def commit_updates(bundle_path, update_info):
    working_directory = os.path.abspath(os.getcwd())
    os.chdir(bundle_path)
    message = ["Automated update by Adabot (adafruit/adabot@{})"
               .format(repo_version())]
    for url, old_commit, new_commit, summary in update_info:
        url_parts = url.split("/")
        user, repo = url_parts[-2:]
        summary = summary.replace("#", "{}/{}#".format(user, repo))
        message.append("Updating {} to {} from {}:\n{}".format(url,
                                                               new_commit,
                                                               old_commit,
                                                               summary))
    message = "\n\n".join(message)
    git.add(".")
    git.commit(message=message)
    os.chdir(working_directory)

if __name__ == "__main__":
    directory = ".bundles"
    for bundle in bundles[:1]:
        bundle_path = os.path.abspath(os.path.join(directory, bundle))
        #fetch_bundle(bundle, bundle_path)
        update_info = update_bundle(bundle_path)
        if update_info:
            commit_updates(bundle_path, update_info)
