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
import datetime
import re

import requests

from adabot import github_requests as github
from adabot import travis_requests as travis
from adabot import pypi_requests as pypi
from adabot.lib import common_funcs
from adabot.lib import assign_hacktober_label as hacktober


# Define constants for error strings to make checking against them more robust:
ERROR_ENABLE_TRAVIS = "Unable to enable Travis build"
ERROR_README_DOWNLOAD_FAILED = "Failed to download README"
ERROR_README_IMAGE_MISSING_ALT = "README image missing alt text"
ERROR_README_DUPLICATE_ALT_TEXT = "README has duplicate alt text"
ERROR_README_MISSING_DISCORD_BADGE = "README missing Discord badge"
ERROR_README_MISSING_RTD_BADGE = "README missing ReadTheDocs badge"
ERROR_README_MISSING_CI_BADGE = "README missing CI badge"
ERROR_README_MISSING_CI_ACTIONS_BADGE = "README CI badge needs to be changed" \
" to GitHub Actions"
ERROR_PYFILE_DOWNLOAD_FAILED = "Failed to download .py code file"
ERROR_PYFILE_MISSING_STRUCT = ".py file contains reference to import ustruct" \
" without reference to import struct.  See issue " \
"https://github.com/adafruit/circuitpython/issues/782"
ERROR_PYFILE_MISSING_RE = ".py file contains reference to import ure" \
" without reference to import re.  See issue " \
"https://github.com/adafruit/circuitpython/issues/1582"
ERROR_PYFILE_MISSING_JSON = ".py file contains reference to import ujson" \
" without reference to import json.  See issue " \
"https://github.com/adafruit/circuitpython/issues/1582"
ERROR_PYFILE_MISSING_ERRNO = ".py file contains reference to import uerrno" \
" without reference to import errno.  See issue " \
"https://github.com/adafruit/circuitpython/issues/1582"
ERROR_MISMATCHED_READTHEDOCS = "Mismatched readthedocs.yml"
ERROR_MISSING_EXAMPLE_FILES = "Missing .py files in examples folder"
ERROR_MISSING_EXAMPLE_FOLDER = "Missing examples folder"
ERROR_EXAMPLE_MISSING_SENSORNAME = "Example file(s) missing sensor/library name"
ERROR_MISSING_EXAMPLE_SIMPLETEST = "Missing simpletest example."
ERROR_MISSING_STANDARD_LABELS = "Missing one or more standard issue labels (bug, documentation, enhancement, good first issue)."
ERROR_MISSING_LIBRARIANS = "CircuitPythonLibrarians team missing or does not have write access"
ERROR_MISSING_LICENSE = "Missing license."
ERROR_MISSING_LINT = "Missing lint config"
ERROR_MISSING_CODE_OF_CONDUCT = "Missing CODE_OF_CONDUCT.md"
ERROR_MISSING_README_RST = "Missing README.rst"
ERROR_MISSING_READTHEDOCS = "Missing readthedocs.yml"
ERROR_MISSING_TRAVIS_CONFIG = "Missing .travis.yml"
ERROR_MISSING_PYPIPROVIDER = "For pypi compatibility, missing pypi provider in .travis.yml"
ERROR_MISSING_SETUP_PY = "For pypi compatibility, missing setup.py"
ERROR_MISSING_REQUIREMENTS_TXT = "For pypi compatibility, missing requirements.txt"
ERROR_MISSING_BLINKA = "For pypi compatibility, missing Adafruit-Blinka in requirements.txt"
ERROR_NOT_IN_BUNDLE = "Not in bundle."
ERROR_TRAVIS_DOESNT_KNOW_REPO = "Travis doesn't know of repo"
ERROR_TRAVIS_ENV = "Unable to read Travis env variables"
ERROR_TRAVIS_GITHUB_TOKEN = "Unable to find or create (no auth) GITHUB_TOKEN env variable"
ERROR_TRAVIS_TOKEN_CREATE = "Token creation failed"
ERROR_UNABLE_PULL_REPO_CONTENTS = "Unable to pull repo contents"
ERROR_UNABLE_PULL_REPO_DETAILS = "Unable to pull repo details"
ERRRO_UNABLE_PULL_REPO_EXAMPLES = "Unable to retrieve examples folder contents"
ERROR_WIKI_DISABLED = "Wiki should be disabled"
ERROR_ONLY_ALLOW_MERGES = "Only allow merges, disallow rebase and squash"
ERROR_RTD_SUBPROJECT_FAILED = "Failed to list CircuitPython subprojects on ReadTheDocs"
ERROR_RTD_SUBPROJECT_MISSING = "ReadTheDocs missing as a subproject on CircuitPython"
ERROR_RTD_ADABOT_MISSING = "ReadTheDocs project missing adabot as owner"
ERROR_RTD_VALID_VERSIONS_FAILED = "Failed to fetch ReadTheDocs valid versions"
ERROR_RTD_FAILED_TO_LOAD_BUILDS = "Unable to load builds webpage"
ERROR_RTD_FAILED_TO_LOAD_BUILD_INFO = "Failed to load build info"
ERROR_RTD_OUTPUT_HAS_WARNINGS = "ReadTheDocs latest build has warnings and/or errors"
ERROR_RTD_AUTODOC_FAILED = "Autodoc failed on ReadTheDocs. (Likely need to automock an import.)"
ERROR_RTD_SPHINX_FAILED = "Sphinx missing files"
ERROR_GITHUB_RELEASE_FAILED = "Failed to fetch latest release from GitHub"
ERROR_GITHUB_NO_RELEASE = "Library repository has no releases"
ERROR_GITHUB_COMMITS_SINCE_LAST_RELEASE_GTM = "Library has new commits since last release over a month ago"
ERROR_GITHUB_COMMITS_SINCE_LAST_RELEASE_1M = "Library has new commits since last release within the last month"
ERROR_GITHUB_COMMITS_SINCE_LAST_RELEASE_1W = "Library has new commits since last release within the last week"
ERROR_RTD_MISSING_LATEST_RELEASE = "ReadTheDocs missing the latest release. (Ignore me! RTD doesn't update when a new version is released. Only on pushes.)"
ERROR_DRIVERS_PAGE_DOWNLOAD_FAILED = "Failed to download drivers page from CircuitPython docs"
ERROR_DRIVERS_PAGE_DOWNLOAD_MISSING_DRIVER = "CircuitPython drivers page missing driver"
ERROR_UNABLE_PULL_REPO_DIR = "Unable to pull repository directory"
ERROR_UNABLE_PULL_REPO_EXAMPLES = "Unable to pull repository examples files"
ERROR_NOT_ON_PYPI = "Not listed on PyPi for CPython use"
ERROR_PYLINT_VERSION_NOT_FIXED = "PyLint version not fixed"
ERROR_PYLINT_VERSION_VERY_OUTDATED = "PyLint version very out of date"
ERROR_PYLINT_VERSION_NOT_LATEST = "PyLint version not latest"
ERROR_NEW_REPO_IN_WORK = "New repo(s) currently in work, and unreleased"

# Temp category for GitHub Actions migration.
ERROR_NEEDS_ACTION_MIGRATION = "Repo(s) need to be migrated from TravisCI to GitHub Actions"

# Since this has been refactored into a separate module, the connection to 'output_handler()'
# and associated 'file_data' list is broken. To keep from possibly having conflicted
# file operations, and writing to the `output_filename` concurrently, establish an
# output_handler error flag, so that the calling function can handle it. Information related
# to the flag will be stored in a instance variable.
ERROR_OUTPUT_HANDLER = "A programmatic error occurred"

# These are warnings or errors that sphinx generate that we're ok ignoring.
RTD_IGNORE_NOTICES = ("WARNING: html_static_path entry", "WARNING: nonlocal image URI found:")

# Constant for bundle repo name.
BUNDLE_REPO_NAME = "Adafruit_CircuitPython_Bundle"

# Repos to ignore for validation they exist in the bundle.  Add repos by their
# full name on Github (like Adafruit_CircuitPython_Bundle).
BUNDLE_IGNORE_LIST = [BUNDLE_REPO_NAME]

LIBRARIES_DONT_NEED_BLINKA = [
    "Adafruit_CircuitPython_BusDevice",
    "Adafruit_CircuitPython_CircuitPlayground",
    "Adafruit_CircuitPython_FancyLED",
    "Adafruit_CircuitPython_IRRemote",
    "Adafruit_CircuitPython_ImageLoad",
    "Adafruit_CircuitPython_MCP9808",
    "Adafruit_CircuitPython_PCA9685",
    "Adafruit_CircuitPython_PCF8523",
    "Adafruit_CircuitPython_TLC59711",
    "Adafruit_CircuitPython_Waveform",
    "Adafruit_CircuitPython_miniQR",
]

STD_REPO_LABELS = ("bug", "documentation", "enhancement", "good first issue")

# Cache CircuitPython's subprojects on ReadTheDocs so its not fetched every repo check.
rtd_subprojects = None

# Cache the CircuitPython driver page so we can make sure every driver is linked to.
core_driver_page = None

class library_validator():
    """ Class to hold instance variables needed to traverse the calling
        code, and the validator functions.
    """

    def __init__(self, validators, bundle_submodules, latest_pylint, **kw_args):
        self.validators = validators
        self.bundle_submodules = bundle_submodules
        self.latest_pylint = latest_pylint
        self.full_auth = None
        self.output_file_data = []
        self.github_token = kw_args.get("github_token", False)
        self.validate_contents_quiet = kw_args.get("validate_contents_quiet", False)

    def run_repo_validation(self, repo):
        """Run all the current validation functions on the provided repository and
        return their results as a list of string errors.
        """
        errors = []
        for validator in self.validators:
            errors.extend(validator(self, repo))
        return errors

    def validate_repo_state(self, repo):
        """Validate a repository meets current CircuitPython criteria.  Expects
        a dictionary with a GitHub API repository state (like from the list_repos
        function).  Returns a list of string error messages for the repository.
        """
        if not (repo["owner"]["login"] == "adafruit" and
                repo["name"].startswith("Adafruit_CircuitPython")):
            return []
        full_repo = github.get("/repos/" + repo["full_name"])
        if not full_repo.ok:
            return [ERROR_UNABLE_PULL_REPO_DETAILS]
        full_repo = full_repo.json()
        errors = []
        if repo["has_wiki"]:
            errors.append(ERROR_WIKI_DISABLED)
        if not repo["license"] and not repo["name"] in BUNDLE_IGNORE_LIST:
            errors.append(ERROR_MISSING_LICENSE)
        if not repo["permissions"]["push"]:
            errors.append(ERROR_MISSING_LIBRARIANS)
        if (not common_funcs.is_repo_in_bundle(full_repo["clone_url"], self.bundle_submodules)
            and not repo["name"] in BUNDLE_IGNORE_LIST):
                # Don't assume the bundle will bundle itself and possibly
                # other repos.
                errors.append(ERROR_NOT_IN_BUNDLE)
        if ("allow_squash_merge" not in full_repo
            or full_repo["allow_squash_merge"]
            or full_repo["allow_rebase_merge"]):
                errors.append(ERROR_ONLY_ALLOW_MERGES)
        return errors

    def validate_release_state(self, repo):
        """Validate if a repo 1) has a release, and 2) if there have been commits
        since the last release.

        If 2), categorize by length of time passed since oldest commit after the release,
        and return the number of days that have passed since the oldest commit.
        """
        if not (repo["owner"]["login"] == "adafruit" and
                repo["name"].startswith("Adafruit_CircuitPython")):
            return []

        if repo["name"] in BUNDLE_IGNORE_LIST:
            return []

        repo_last_release = github.get("/repos/"
                                       + repo["full_name"]
                                       + "/releases/latest")
        if not repo_last_release.ok:
            return [ERROR_GITHUB_NO_RELEASE]
        repo_release_json = repo_last_release.json()
        if "tag_name" in repo_release_json:
            tag_name = repo_release_json["tag_name"]
        elif "message" in repo_release_json:
            if repo_release_json["message"] == "Not Found":
                return [ERROR_GITHUB_NO_RELEASE]
            else:
                # replace 'output_handler' with ERROR_OUTPUT_HANDLER
                err_msg = [
                    "Error: retrieving latest release information failed on ",
                    "'{}'. ".format(repo["name"]),
                    "Information Received: ",
                    "{}".format(repo_release_json["message"])
                ]
                self.output_file_data.append("".join(err_msg))
                return [ERROR_OUTPUT_HANDLER]

        compare_tags = github.get("/repos/"
                                  + repo["full_name"]
                                  + "/compare/"
                                  + tag_name
                                  + "...master")
        if not compare_tags.ok:
            # replace 'output_handler' with ERROR_OUTPUT_HANDLER
            err_msg = [
                "Error: failed to compare {} 'master' ".format(repo["name"]),
                "to tag '{}'".format(tag_name)
            ]
            self.output_file_data.append("".join(err_msg))
            return [ERROR_OUTPUT_HANDLER]
        compare_tags_json = compare_tags.json()
        if "status" in compare_tags_json:
            if compare_tags.json()["status"] != "identical":
                oldest_commit_date = datetime.datetime.today()
                for commit in compare_tags_json["commits"]:
                    commit_date = datetime.datetime.strptime(commit["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ")
                    if commit_date < oldest_commit_date:
                        oldest_commit_date = commit_date

                date_diff = datetime.datetime.today() - oldest_commit_date
                #print("{0} Release State:\n  Tag Name: {1}\tRelease Date: {2}\n  Today: {3}\t Released {4} days ago.".format(repo["name"], tag_name, oldest_commit_date, datetime.datetime.today(), date_diff.days))
                #print("Compare {4} status: {0} \n  Ahead: {1} \t Behind: {2} \t Commits: {3}".format(
                #      compare_tags_json["status"], compare_tags_json["ahead_by"],
                #      compare_tags_json["behind_by"], compare_tags_json["total_commits"], repo["full_name"]))
                if date_diff.days > datetime.date.today().max.day:
                    return [(ERROR_GITHUB_COMMITS_SINCE_LAST_RELEASE_GTM,
                            date_diff.days)]
                elif date_diff.days <= datetime.date.today().max.day:
                    if date_diff.days > 7:
                        return [(ERROR_GITHUB_COMMITS_SINCE_LAST_RELEASE_1M,
                                date_diff.days)]
                    else:
                        return [(ERROR_GITHUB_COMMITS_SINCE_LAST_RELEASE_1W,
                                date_diff.days)]
        elif "errors" in compare_tags_json:
            # replace 'output_handler' with ERROR_OUTPUT_HANDLER
            err_msg = [
                "Error: comparing latest release to 'master' failed on ",
                "'{}'. ".format(repo["name"]),
                "Error Message: {}".format(compare_tags_json["message"])
            ]
            self.output_file_data.append("".join(err_msg))
            return [ERROR_OUTPUT_HANDLER]

        return []

    def _validate_readme(self, repo, download_url):
        # We use requests because file contents are hosted by
        # githubusercontent.com, not the API domain.
        contents = requests.get(download_url, timeout=30)
        if not contents.ok:
            return [ERROR_README_DOWNLOAD_FAILED]

        errors = []
        badges = {}
        current_image = None
        for line in contents.text.split("\n"):
            if line.startswith(".. image"):
                current_image = {}

            if line.strip() == "" and current_image is not None:
                if "alt" not in current_image:
                    errors.append(ERROR_README_IMAGE_MISSING_ALT)
                elif current_image["alt"] in badges:
                    errors.append(ERROR_README_DUPLICATE_ALT_TEXT)
                else:
                    badges[current_image["alt"]] = current_image
                current_image = None
            elif current_image is not None:
                first, second, value = line.split(":", 2)
                key = first.strip(" .") + second.strip()
                current_image[key] = value.strip()

        if "Discord" not in badges:
            errors.append(ERROR_README_MISSING_DISCORD_BADGE)

        if "Documentation Status" not in badges:
            errors.append(ERROR_README_MISSING_RTD_BADGE)

        if "Build Status" not in badges:
            errors.append(ERROR_README_MISSING_CI_BADGE)
        else:
            status_img = badges["Build Status"]["image"]
            if "travis-ci.com" in status_img:
                errors.append(ERROR_README_MISSING_CI_ACTIONS_BADGE)

        return errors

    def _validate_py_for_u_modules(self, repo, download_url):
        """ For a .py file, look for usage of "import u___" and
            look for "import ___".  If the "import u___" is
            used with NO "import ____" generate an error.
        """
        # We use requests because file contents are hosted by
        # githubusercontent.com, not the API domain.
        contents = requests.get(download_url, timeout=30)
        if not contents.ok:
            return [ERROR_PYFILE_DOWNLOAD_FAILED]

        errors = []

        lines = contents.text.split("\n")
        ustruct_lines = ([l for l in lines
                         if re.match(r"[\s]*import[\s][\s]*ustruct", l)])
        struct_lines = ([l for l in lines
                        if re.match(r"[\s]*import[\s][\s]*struct", l)])
        if ustruct_lines and not struct_lines:
            errors.append(ERROR_PYFILE_MISSING_STRUCT)

        ure_lines = ([l for l in lines
                     if re.match(r"[\s]*import[\s][\s]*ure", l)])
        re_lines = ([l for l in lines
                    if re.match(r"[\s]*import[\s][\s]*re", l)])
        if ure_lines and not re_lines:
            errors.append(ERROR_PYFILE_MISSING_RE)

        ujson_lines = ([l for l in lines
                       if re.match(r"[\s]*import[\s][\s]*ujson", l)])
        json_lines = ([l for l in lines
                      if re.match(r"[\s]*import[\s][\s]*json", l)])
        if ujson_lines and not json_lines:
            errors.append(ERROR_PYFILE_MISSING_JSON)

        uerrno_lines = ([l for l in lines
                        if re.match(r"[\s]*import[\s][\s]*uerrno", l)])
        errno_lines = ([l for l in lines
                       if re.match(r"[\s]*import[\s][\s]*errno", l)])
        if uerrno_lines and not errno_lines:
            errors.append(ERROR_PYFILE_MISSING_ERRNO)

        return errors

    def _validate_travis_yml(self, repo, travis_yml_file_info):
        """DISABLED/NO LONGER CALLED: Check size and then check pypi compatibility.
        """
        return []

        download_url = travis_yml_file_info["download_url"]
        contents = requests.get(download_url, timeout=30)
        if not contents.ok:
            return [ERROR_PYFILE_DOWNLOAD_FAILED]

        errors = []

        lines = contents.text.split("\n")
        pypi_providers_lines = (
            [l for l in lines
            if re.match(r"[\s]*-[\s]*provider:[\s]*pypi[\s]*", l)]
        )

        if not pypi_providers_lines:
            errors.append(ERROR_MISSING_PYPIPROVIDER)

        pylint_version = None
        for line in lines:
            if not line.strip().startswith("- pip install --force-reinstall pylint=="):
                continue
            pylint_version = line.split("=")[-1]

        if not pylint_version:
            errors.append(ERROR_PYLINT_VERSION_NOT_FIXED)
        # disabling below for now, since we know all pylint versions are old
        # will re-enable once efforts are underway to update pylint
        #elif pylint_version.startswith("1."):
        #    errors.append(ERROR_PYLINT_VERSION_VERY_OUTDATED)
        #elif pylint_version != self.latest_pylint:
        #    errors.append(ERROR_PYLINT_VERSION_NOT_LATEST)

        return errors

    def _validate_setup_py(self, repo, file_info):
        """Check setup.py for pypi compatibility
        """
        download_url = file_info["download_url"]
        contents = requests.get(download_url, timeout=30)
        if not contents.ok:
            return [ERROR_PYFILE_DOWNLOAD_FAILED]

        errors = []


        return errors

    def _validate_requirements_txt(self, repo, file_info):
        """Check requirements.txt for pypi compatibility
        """
        download_url = file_info["download_url"]
        contents = requests.get(download_url, timeout=30)
        if not contents.ok:
            return [ERROR_PYFILE_DOWNLOAD_FAILED]

        errors = []
        lines = contents.text.split("\n")
        blinka_lines = ([l for l in lines
                        if re.match(r"[\s]*Adafruit-Blinka[\s]*", l)])

        if not blinka_lines and repo["name"] not in LIBRARIES_DONT_NEED_BLINKA:
            errors.append(ERROR_MISSING_BLINKA)
        return errors

    def validate_contents(self, repo):
        """Validate the contents of a repository meets current CircuitPython
        criteria (within reason, functionality checks are not possible).  Expects
        a dictionary with a GitHub API repository state (like from the list_repos
        function).  Returns a list of string error messages for the repository.
        """

        if not (repo["owner"]["login"] == "adafruit" and
                repo["name"].startswith("Adafruit_CircuitPython")):
            return []
        if repo["name"] == BUNDLE_REPO_NAME:
            return []

        content_list = github.get("/repos/" + repo["full_name"] + "/contents/")
        empty_repo = False
        if not content_list.ok:
            # Empty repos return:
            #  - a 404 status code
            #  - a "message" that the repo is empty.
            if "message" in content_list.json():
                if "empty" in content_list.json()["message"]:
                    empty_repo = True
            if not empty_repo:
                if not self.validate_contents_quiet:
                    return [ERROR_UNABLE_PULL_REPO_CONTENTS]
                return []

        content_list = content_list.json()
        files = []
        # an empty repo will return a 'message'
        if not empty_repo:
            files = [x["name"] for x in content_list]

        # ignore new/in-work repos, which should have less than 8 files:
        # ___.py or folder, CoC, .travis.yml, .readthedocs.yml, docs/,
        # examples/, README, LICENSE
        if len(files) < 8:
            BUNDLE_IGNORE_LIST.append(repo["name"])
            if not self.validate_contents_quiet:
                return [ERROR_NEW_REPO_IN_WORK]

        # if we're only running due to -v, ignore the rest. we only care about
        # adding in-work repos to the BUNDLE_IGNORE_LIST
        if self.validate_contents_quiet:
            return []

        errors = []
        if ".pylintrc" not in files:
            errors.append(ERROR_MISSING_LINT)

        if "CODE_OF_CONDUCT.md" not in files:
            errors.append(ERROR_MISSING_CODE_OF_CONDUCT)

        if "README.rst" not in files:
            errors.append(ERROR_MISSING_README_RST)
        else:
            readme_info = None
            for f in content_list:
                if f["name"] == "README.rst":
                    readme_info = f
                    break
            errors.extend(self._validate_readme(repo,
                                                readme_info["download_url"]))

        if ".travis.yml" in files:
            errors.append(ERROR_NEEDS_ACTION_MIGRATION)

        if "readthedocs.yml" in files or ".readthedocs.yml" in files:
            fn = "readthedocs.yml"
            if ".readthedocs.yml" in files:
                fn = ".readthedocs.yml"
            file_info = content_list[files.index(fn)]
            if (file_info["sha"] != "f4243ad548bc5e4431f2d3c5d486f6c9c863888b" and
               file_info["sha"] != "78a4671650248f4382e6eb72dab71c2d86824ca2"):
                errors.append(ERROR_MISMATCHED_READTHEDOCS)
        else:
            errors.append(ERROR_MISSING_READTHEDOCS)

        if "setup.py" in files:
            file_info = content_list[files.index("setup.py")]
            errors.extend(self._validate_setup_py(repo, file_info))
        else:
            errors.append(ERROR_MISSING_SETUP_PY)

        if "requirements.txt" in files:
            file_info = content_list[files.index("requirements.txt")]
            errors.extend(self._validate_requirements_txt(repo, file_info))
        else:
            errors.append(ERROR_MISSING_REQUIREMENTS_TXT)


        #Check for an examples folder.
        dirs = [
            x["url"] for x in content_list
            if (x["type"] == "dir" and x["name"] == "examples")
        ]
        examples_list = []
        if dirs:
            while dirs:
                # loop through the results to ensure we capture files
                # in subfolders, and add any files in the current directory
                result = github.get(dirs.pop(0))
                if not result.ok:
                    errors.append(ERROR_UNABLE_PULL_REPO_EXAMPLES)
                    break
                result_json = result.json()
                dirs.extend([x["url"] for x in result_json if x["type"] == "dir"])
                examples_list.extend([x for x in result_json if x["type"] == "file"])

            if len(examples_list) < 1:
                errors.append(ERROR_MISSING_EXAMPLE_FILES)
            else:
                lib_name = (repo["name"][repo["name"].rfind("CircuitPython_")
                            + 14:].lower())
                all_have_name = True
                simpletest_exists = False
                for example in examples_list:
                    if (not example["name"].lower().startswith(lib_name)
                        and example["name"].endswith(".py")):
                            all_have_name = False
                    if "simpletest" in example["name"].lower():
                        simpletest_exists = True
                if not all_have_name:
                    errors.append(ERROR_EXAMPLE_MISSING_SENSORNAME)
                if not simpletest_exists:
                    errors.append(ERROR_MISSING_EXAMPLE_SIMPLETEST)
        else:
            errors.append(ERROR_MISSING_EXAMPLE_FOLDER)

        # first location .py files whose names begin with "adafruit_"
        re_str = re.compile('adafruit\_[\w]*\.py')
        pyfiles = ([x["download_url"] for x in content_list
                   if re_str.fullmatch(x["name"])])
        for pyfile in pyfiles:
            # adafruit_xxx.py file; check if for proper usage of u___ versions of modules
            errors.extend(self._validate_py_for_u_modules(repo, pyfile))

        # now location any directories whose names begin with "adafruit_"
        re_str = re.compile('adafruit\_[\w]*')
        for adir in dirs:
            if re_str.fullmatch(adir):
                # retrieve the files in that directory
                dir_file_list = github.get("/repos/"
                                           + repo["full_name"]
                                           + "/contents/"
                                           + adir)
                if not dir_file_list.ok:
                    errors.append(ERROR_UNABLE_PULL_REPO_DIR)
                dir_file_list = dir_file_list.json()
                # search for .py files in that directory
                dir_files = ([x["download_url"] for x in dir_file_list
                             if x["type"] == "file"
                             and x["name"].endswith(".py")])
                for dir_file in dir_files:
                    # .py files in subdirectory adafruit_xxx
                    # check if for proper usage of u___ versions of modules
                    errors.extend(self._validate_py_for_u_modules(repo, dir_file))

        return errors

    def _validate_travis(self, repo):
        """ DISABLED: Validate and configure a repository has the expected state in Travis
        CI.  This will both check Travis state and attempt to enable Travis CI
        and setup the expected state in Travis if not enabled.  Expects a
        dictionary with a GitHub API repository state (like from the list_repos
        function).  Returns a list of string error messages for the repository.
        """
        return []

        if not (repo["owner"]["login"] == "adafruit" and
                repo["name"].startswith("Adafruit_CircuitPython")):
            return []
        repo_url = "/repo/" + repo["owner"]["login"] + "%2F" + repo["name"]
        result = travis.get(repo_url)
        if not result.ok:
            #print(result, result.request.url, result.request.headers)
            #print(result.text)
            return [ERROR_TRAVIS_DOESNT_KNOW_REPO]
        result = result.json()
        if not result["active"]:
            activate = travis.post(repo_url + "/activate")
            if not activate.ok:
                #print(activate.request.url)
                #print("{} {}".format(activate, activate.text))
                return [ERROR_ENABLE_TRAVIS]

        env_variables = travis.get(repo_url + "/env_vars")
        if not env_variables.ok:
            #print(env_variables, env_variables.text)
            #print(env_variables.request.headers)
            return [ERROR_TRAVIS_ENV]
        env_variables = env_variables.json()
        found_token = False
        for var in env_variables["env_vars"]:
            found_token = found_token or var["name"] == "GITHUB_TOKEN"
        ok = True
        if not found_token:
            if not self.github_token:
                return [ERROR_TRAVIS_GITHUB_TOKEN]
            else:
                if not self.full_auth:
                    #github_user = github_token
                    github_user = github.get("/user").json()
                    password = input("Password for " + github_user["login"] + ": ")
                    self.full_auth = (github_user["login"], password.strip())
                if not self.full_auth:
                    return [ERROR_TRAVIS_GITHUB_TOKEN]

                new_access_token = {"scopes": ["public_repo"],
                                    "note": "TravisCI release token for " + repo["full_name"],
                                    "note_url": "https://travis-ci.com/" + repo["full_name"]}
                token = github.post("/authorizations", json=new_access_token, auth=self.full_auth)
                if not token.ok:
                    print(token.text)
                    return [ERROR_TRAVIS_TOKEN_CREATE]

                token = token.json()
                grant_id = token["id"]
                token = token["token"]

                new_var = {"env_var.name": "GITHUB_TOKEN",
                           "env_var.value": token,
                           "env_var.public": False}
                new_var_result = travis.post(repo_url + "/env_vars", json=new_var)
                if not new_var_result.ok:
                    #print(new_var_result.headers, new_var_result.text)
                    github.delete("/authorizations/{}".format(grant_id), auth=self.full_auth)
                    return [ERROR_TRAVIS_GITHUB_TOKEN]

        return []

    def validate_readthedocs(self, repo):
        if not (repo["owner"]["login"] == "adafruit" and
                repo["name"].startswith("Adafruit_CircuitPython")):
            return []
        if repo["name"] in BUNDLE_IGNORE_LIST:
            return []
        global rtd_subprojects
        if not rtd_subprojects:
            rtd_response = requests.get("https://readthedocs.org/api/v2/project/74557/subprojects/",
                                        timeout=15)
            if not rtd_response.ok:
                return [ERROR_RTD_SUBPROJECT_FAILED]
            rtd_subprojects = {}
            for subproject in rtd_response.json()["subprojects"]:
                rtd_subprojects[common_funcs.sanitize_url(subproject["repo"])] = subproject

        repo_url = common_funcs.sanitize_url(repo["clone_url"])
        if repo_url not in rtd_subprojects:
            return [ERROR_RTD_SUBPROJECT_MISSING]

        errors = []
        subproject = rtd_subprojects[repo_url]

        if 105398 not in subproject["users"]:
            errors.append(ERROR_RTD_ADABOT_MISSING)

        valid_versions = requests.get(
            "https://readthedocs.org/api/v2/project/{}/active_versions/".format(subproject["id"]),
            timeout=15)
        if not valid_versions.ok:
            errors.append(ERROR_RTD_VALID_VERSIONS_FAILED)
        else:
            valid_versions = valid_versions.json()
            latest_release = github.get("/repos/{}/releases/latest".format(repo["full_name"]))
            if not latest_release.ok:
                errors.append(ERROR_GITHUB_RELEASE_FAILED)
            # disabling this for now, since it is ignored and always fails
            #else:
            #    if latest_release.json()["tag_name"] not in [tag["verbose_name"] for tag in valid_versions["versions"]]:
            #        errors.append(ERROR_RTD_MISSING_LATEST_RELEASE)

        # There is no API which gives access to a list of builds for a project so we parse the html
        # webpage.
        builds_webpage = requests.get(
            "https://readthedocs.org/projects/{}/builds/".format(subproject["slug"]),
            timeout=15)
        if not builds_webpage.ok:
            errors.append(ERROR_RTD_FAILED_TO_LOAD_BUILDS)
        else:
            for line in builds_webpage.text.split("\n"):
                if "<div id=\"build-" in line:
                    build_id = line.split("\"")[1][len("build-"):]
                # We only validate the most recent, latest build. So, break when the first "version
                # latest" found. Its in the page after the build id.
                if "version latest" in line:
                    break
            build_info = requests.get("https://readthedocs.org/api/v2/build/{}/".format(build_id),
                                      timeout=15)
            if not build_info.ok:
                errors.append(ERROR_RTD_FAILED_TO_LOAD_BUILD_INFO)
            else:
                build_info = build_info.json()
                output_ok = True
                autodoc_ok = True
                sphinx_ok = True
                for command in build_info["commands"]:
                    if command["command"].endswith("_build/html"):
                        for line in command["output"].split("\n"):
                            if "... " in line:
                                _, line = line.split("... ")
                            if "WARNING" in line or "ERROR" in line:
                                if not line.startswith(("WARNING", "ERROR")):
                                    line = line.split(" ", 1)[1]
                                if not line.startswith(RTD_IGNORE_NOTICES):
                                    output_ok = False
                            elif line.startswith("ImportError"):
                                autodoc_ok = False
                            elif line.startswith("sphinx.errors") or line.startswith("SphinxError"):
                                sphinx_ok = False
                        break
                if not output_ok:
                    errors.append(ERROR_RTD_OUTPUT_HAS_WARNINGS)
                if not autodoc_ok:
                    errors.append(ERROR_RTD_AUTODOC_FAILED)
                if not sphinx_ok:
                    errors.append(ERROR_RTD_SPHINX_FAILED)

        return errors

    def validate_core_driver_page(self, repo):
        if not (repo["owner"]["login"] == "adafruit" and
                repo["name"].startswith("Adafruit_CircuitPython")):
            return []
        if repo["name"] in BUNDLE_IGNORE_LIST:
            return []
        global core_driver_page
        if not core_driver_page:
            driver_page = requests.get("https://raw.githubusercontent.com/adafruit/Adafruit_CircuitPython_Bundle/master/docs/drivers.rst",
                                       timeout=15)
            if not driver_page.ok:
                return [ERROR_DRIVERS_PAGE_DOWNLOAD_FAILED]
            core_driver_page = driver_page.text

        repo_short_name = repo["name"][len("Adafruit_CircuitPython_"):].lower()
        full_url = "https://circuitpython.readthedocs.io/projects/" + repo_short_name + "/en/latest/"
        full_url_dashes = full_url.replace("_", "-")
        if full_url not in core_driver_page and full_url_dashes not in core_driver_page:
            return [ERROR_DRIVERS_PAGE_DOWNLOAD_MISSING_DRIVER]
        return []



    def gather_insights(self, repo, insights, since):
        """Gather analytics about a repository like open and merged pull requests.
        This expects a dictionary with GitHub API repository state (like from the
        list_repos function) and will fill in the provided insights dictionary
        with analytics it computes for the repository.
        """

        if repo["owner"]["login"] != "adafruit":
            return []
        params = {"sort": "updated",
                  "state": "all",
                  "since": since.strftime("%Y-%m-%dT%H:%M:%SZ")}
        response = github.get("/repos/" + repo["full_name"] + "/issues", params=params)
        if not response.ok:
            # replace 'output_handler' with ERROR_OUTPUT_HANDLER
            self.output_file_data.append("Insights request failed: {}".format(repo["full_name"]))
            return [ERROR_OUTPUT_HANDLER]

        issues = response.json()
        for issue in issues:
            created = datetime.datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            if "pull_request" in issue:
                pr_info = github.get(issue["pull_request"]["url"])
                pr_info = pr_info.json()
                if issue["state"] == "open":
                    if created > since:
                        insights["new_prs"] += 1
                        insights["pr_authors"].add(pr_info["user"]["login"])
                    insights["active_prs"] += 1
                else:
                    if pr_info["merged"]:
                        insights["merged_prs"] += 1
                        insights["pr_merged_authors"].add(pr_info["user"]["login"])
                        insights["pr_reviewers"].add(pr_info["merged_by"]["login"])
                        pr_reviews = github.get(str(pr_info["url"]) + "/reviews")
                        if pr_reviews.ok:
                            for review in pr_reviews.json():
                                if review["state"].lower() == "approved":
                                    insights["pr_reviewers"].add(review["user"]["login"])
                    else:
                        insights["closed_prs"] += 1
            else:
                issue_info = github.get(issue["url"])
                issue_info = issue_info.json()
                if issue["state"] == "open":
                    if created > since:
                        insights["new_issues"] += 1
                        insights["issue_authors"].add(issue_info["user"]["login"])
                    insights["active_issues"] += 1
                else:
                    insights["closed_issues"] += 1
                    insights["issue_closers"].add(issue_info["closed_by"]["login"])

        issues = []
        params = {"state": "open", "per_page": 100}
        response = github.get("/repos/" + repo["full_name"] + "/issues", params=params)
        if not response.ok:
            # replace 'output_handler' with ERROR_OUTPUT_HANDLER
            self.output_file_data.append("Issues request failed: {}".format(repo["full_name"]))
            return [ERROR_OUTPUT_HANDLER]

        while response.ok:
            issues.extend(response.json())
            try:
                links = response.headers["Link"]
            except KeyError:
                break

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
                response = requests.get(link, timeout=30)

        for issue in issues:
            created = datetime.datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            days_open = datetime.datetime.today() - created
            if days_open.days < 0: # opened earlier today
                days_open += datetime.timedelta(days=(days_open.days * -1))
            if "pull_request" in issue:
                pr_link = "{0} (Open {1} days)".format(issue["pull_request"]["html_url"],
                                                       days_open.days)
                insights["open_prs"].append(pr_link)
            else:
                issue_link = "{0} (Open {1} days)".format(issue["html_url"],
                                                          days_open.days)
                insights["open_issues"].append(issue_link)

        # process Hacktoberfest labels if it is Hacktoberfest season
        in_season, season_action = hacktober.is_hacktober_season()
        if in_season:
            hacktober_issues = [
                issue for issue in issues if "pull_request" not in issue
            ]
            if season_action == "add":
                insights["hacktober_assigned"] += (
                    hacktober.assign_hacktoberfest(repo,
                                                   issues=hacktober_issues)
                )
            elif season_action == "remove":
                insights["hacktober_removed"] += (
                    hacktober.assign_hacktoberfest(repo,
                                                   issues=hacktober_issues,
                                                   remove_labels=True)
                )

        # get milestones for core repo
        if repo["name"] == "circuitpython":
            params = {"state": "open"}
            response = github.get("/repos/adafruit/circuitpython/milestones", params=params)
            if not response.ok:
                # replace 'output_handler' with ERROR_OUTPUT_HANDLER
                self.output_file_data.append("Failed to get core milestone insights.")
                return [ERROR_OUTPUT_HANDLER]
            else:
                milestones = response.json()
                for milestone in milestones:
                    #print(milestone)
                    insights["milestones"][milestone["title"]] = milestone["open_issues"]
        return []

    def validate_in_pypi(self, repo):
        """prints a list of Adafruit_CircuitPython libraries that are in pypi"""
        if repo["name"] in BUNDLE_IGNORE_LIST:
            return []
        if not (repo["owner"]["login"] == "adafruit" and
                repo["name"].startswith("Adafruit_CircuitPython")):
            return []
        if not common_funcs.repo_is_on_pypi(repo):
            return [ERROR_NOT_ON_PYPI]
        return []

    def validate_labels(self, repo):
        """ensures the repo has the standard labels available"""
        response = github.get("/repos/" + repo["full_name"] + "/labels")
        if not response.ok:
            # replace 'output_handler' with ERROR_OUTPUT_HANDLER
            self.output_file_data.append("Labels request failed: {}".format(repo["full_name"]))
            return [ERROR_OUTPUT_HANDLER]

        repo_labels = [label["name"] for label in response.json()]
        has_all_labels = True
        for label in STD_REPO_LABELS:
            if not label in repo_labels:
                has_all_labels = False

        if not has_all_labels:
            return [ERROR_MISSING_STANDARD_LABELS]
        else:
            return []
