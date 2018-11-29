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
import copy
import datetime
import re
import sys
import argparse
import traceback

import requests

from adabot import github_requests as github

def list_repos():
    """Return a list of all Adafruit repositories that start with
    Adafruit_CircuitPython.  Each list item is a dictionary of GitHub API
    repository state.
    """
    repos = []
    result = github.get("/search/repositories",
                        params={"q":"Arduino in:name in:description in:readme fork:true user:adafruit archived:false",
                                "per_page": 100,
                                "sort": "updated",
                                "order": "asc"})
    while result.ok:
        links = result.headers["Link"]
        repos.extend(result.json()["items"]) # uncomment and comment below, to include all forks

        if links:
            next_url = None
            for link in links.split(","):
                link, rel = link.split(";")
                link = link.strip(" <>")
                rel = rel.strip()
                if rel == "rel=\"next\"":
                    next_url = link
                    break
            if not next_url:
                break
            # Subsequent links have our access token already so we use requests directly.
            result = requests.get(link, timeout=30)

    return repos

def validate_library_properties(repo):
    has_lib_prop = github.get("/repos/adafruit/" + repo["name"] + "/contents")
    if has_lib_prop.ok:
        if "library.properties" not in has_lib_prop.text:
            return
        lib_prop_file = None
        for file in has_lib_prop.json():
            if file["name"] == "library.properties":
                lib_prop_file = requests.get(file["download_url"], timeout=30)
                if lib_prop_file.ok:
                    lines = lib_prop_file.text.split("\n")
                    for line in lines:
                        if "version" in line:
                            lib_version = line[len("version="):]
                            break
    latest_release = github.get("/repos/adafruit/" + repo["name"] + "/releases/latest")
    if latest_release.ok:
        release_tag = latest_release.json()["tag_name"]
        print("{0} Results - library.properties version: {1} | repo release tag: {2}".format(repo["name"], lib_version, release_tag))

if __name__ == "__main__":
    repo_list = list_repos()
    for repo in repo_list:
        validate_library_properties(repo)
