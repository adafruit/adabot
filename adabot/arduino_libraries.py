# The MIT License (MIT)
#
# Copyright (c) 2018 Michael Schroeder
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
import datetime
import sys
import argparse
import traceback

import requests

from adabot import github_requests as github

# Setup ArgumentParser
cmd_line_parser = argparse.ArgumentParser(description="Adabot utility for Arduino Libraries.",
                                          prog="Adabot Arduino Libraries Utility")
cmd_line_parser.add_argument("-o", "--output_file", help="Output log to the filename provided.",
                             metavar="<OUTPUT FILENAME>", dest="output_file")
cmd_line_parser.add_argument("-v", "--verbose", help="Set the level of verbosity printed to the command prompt."
                             " Zero is off; One is on (default).", type=int, default=1, dest="verbose", choices=[0,1])
output_filename = None
verbosity = 1
file_data = []

def list_repos():
    """ Return a list of all Adafruit repositories with 'Arduino' in either the
        name, description, or readme. Each list item is a dictionary of GitHub API
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

def is_arduino_library(repo):
    """ Returns if the repo is an Arduino library, as determined by the existence of
        the 'library.properties' file.
    """
    has_lib_prop = github.get("/repos/adafruit/" + repo["name"] + "/contents")
    if has_lib_prop.ok:
        return ("library.properties" in has_lib_prop.text)
    else:
        return False

def print_list_output(title="", list=[]):
    ""
    output_handler()
    output_handler(title.format(len(list)))
    long_col = [(max([len(str(row[i])) for row in list]) + 3)
                for i in range(len(list[0]))]
    row_format = "".join(["{:<" + str(this_col) + "}" for this_col in long_col])
    for lib in list:
        output_handler(row_format.format(*lib))

def output_handler(message="", quiet=False):
    """Handles message output to prompt/file for print_*() functions."""
    if output_filename is not None:
        file_data.append(message)
    if verbosity and not quiet:
        print(message)

def validate_library_properties(repo):
    """ Checks if the latest GitHub Release Tag and version in the library_properties
        file match. Will also check if the library_properties is there, but no release
        has been made.
    """
    lib_prop_file = None
    lib_version = None
    release_tag = None
    has_lib_prop = github.get("/repos/adafruit/" + repo["name"] + "/contents")
    if has_lib_prop.ok:
        if "library.properties" not in has_lib_prop.text:
            return
        for file in has_lib_prop.json():
            if file["name"] == "library.properties":
                lib_prop_file = requests.get(file["download_url"], timeout=30)
                if lib_prop_file.ok:
                    lines = lib_prop_file.text.split("\n")
                    for line in lines:
                        if "version" in line:
                            lib_version = line[len("version="):]
                            break

        get_latest_release = github.get("/repos/adafruit/" + repo["name"] + "/releases/latest")
        if get_latest_release.ok:
            response = get_latest_release.json()
            if "tag_name" in response:
                release_tag = response["tag_name"]
            if "message" in response:
                if response["message"] == "Not Found":
                    release_tag = "None"
                else:
                    release_tag = "Unknown"

        if lib_version and release_tag:
            return [release_tag, lib_version]

    #print("{} skipped".format(repo["name"]))
    return

def validate_release_state(repo):
    """Validate if a repo 1) has a release, and 2) if there have been commits
    since the last release. Returns a list of string error messages for the
    repository.
    """

    if not is_arduino_library(repo):
        return
    repo_last_release = github.get("/repos/" + repo["full_name"] + "/releases/latest")
    if not repo_last_release.ok:
        return
    repo_release_json = repo_last_release.json()
    if "tag_name" in repo_release_json:
        tag_name = repo_release_json["tag_name"]
    elif "message" in repo_release_json:
        output_handler("Error: retrieving latest release information failed on '{0}'. Information Received: {1}".format(
                           repo["name"], repo_release_json["message"]))
        return

    compare_tags = github.get("/repos/" + repo["full_name"] + "/compare/master..." + tag_name)
    if not compare_tags.ok:
        output_handler("Error: failed to compare {0} 'master' to tag '{1}'".format(repo["name"], tag_name))
        return
    compare_tags_json = compare_tags.json()
    if "status" in compare_tags_json:
        if compare_tags.json()["status"] != "identical":
            #print("Compare {4} status: {0} \n  Ahead: {1} \t Behind: {2} \t Commits: {3}".format(
            #      compare_tags_json["status"], compare_tags_json["ahead_by"],
            #      compare_tags_json["behind_by"], compare_tags_json["total_commits"], repo["full_name"]))
            return [tag_name, compare_tags_json["behind_by"]]
    elif "errors" in compare_tags_json:
        output_handler("Error: comparing latest release to 'master' failed on '{0}'. Error Message: {1}".format(
                       repo["name"], compare_tags_json["message"]))

    return

def validate_travis(repo):
    """Validate if a repo has .travis.yml.
    """
    repo_has_travis = github.get("/repos/" + repo["full_name"] + "/contents/.travis.yml")
    if not repo_has_travis.ok:
        return True

def has_ino(repo):
    """Validate if a repo has any *.ino files.
    """
    repo_has_ino = github.get("/search/code?q=extension:ino+repo:adafruit/" + repo["name"])
    if repo_has_ino.ok and repo_has_ino.json()["total_count"] > 0:
        return True

def has_library_properties(repo):
    """Validate if a repo has library.properties file.
    """
    repo_has_file = github.get("/search/code?q=library+extension:properties+repo:adafruit/" + repo["name"])
    if repo_has_file.ok and repo_has_file.json()["total_count"] > 0:
        return True

def run_arduino_lib_checks():
    output_handler("Running Arduino Library Checks")
    output_handler("Getting list of libraries to check...")

    repo_list = list_repos()
    output_handler("Found {} Arduino libraries to check\n".format(len(repo_list)))
    failed_lib_prop = [["  Repo", "Release Tag", "library.properties Version"], ["  ----", "-----------", "--------------------------"]]
    needs_release_list = [["  Repo", "Latest Release", "Commits Behind"], ["  ----", "--------------", "--------------"]]
    missing_travis_list = [["  Repo"], ["  ----"]]
    missing_library_properties_list = [["  Repo"], ["  ----"]]

    for repo in repo_list:
        lib_check = validate_library_properties(repo)
        if lib_check:
            if lib_check[0] != lib_check[1]:
                failed_lib_prop.append(["  " + str(repo["name"]), lib_check[0], lib_check[1]])

        needs_release = validate_release_state(repo)
        missing_travis = validate_travis(repo) and has_ino(repo)
        missing_library_properties = has_ino(repo) and not has_library_properties(repo)

        if needs_release:
            needs_release_list.append(["  " + str(repo["name"]), needs_release[0], needs_release[1]])

        if missing_travis:
            missing_travis_list.append(["  " + str(repo["name"])])

        if missing_library_properties:
            missing_library_properties_list.append(["  " + str(repo["name"])])

    if len(failed_lib_prop) > 2:
        print_list_output("Libraries Have Mismatched Release Tag and library.properties Version: ({})", failed_lib_prop)

    if len(needs_release_list) > 2:
        print_list_output("Libraries have commits since last release: ({})", needs_release_list);

    if len(missing_travis_list) > 2:
        print_list_output("Libraries that is not configured with Travis (but have *.ino files): ({})", missing_travis_list)

    if len(missing_library_properties_list) > 2:
        print_list_output("Libraries that is missing library.properties file (but have *.ino files): ({})", missing_library_properties_list)


if __name__ == "__main__":
    cmd_line_args = cmd_line_parser.parse_args()
    verbosity = cmd_line_args.verbose
    if cmd_line_args.output_file:
        output_filename = cmd_line_args.output_file

    try:
        run_arduino_lib_checks()
    except:
        if output_filename is not None:
            exc_type, exc_val, exc_tb = sys.exc_info()
            output_handler("Exception Occurred!", quiet=True)
            output_handler(("-"*60), quiet=True)
            output_handler("Traceback (most recent call last):", quiet=True)
            tb = traceback.format_tb(exc_tb)
            for line in tb:
                output_handler(line, quiet=True)
            output_handler(exc_val, quiet=True)

        raise
    finally:
        if output_filename is not None:
            with open(output_filename, 'w') as f:
                for line in file_data:
                    f.write(str(line) + "\n")
