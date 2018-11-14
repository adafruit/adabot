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
from adabot import travis_requests as travis
from adabot import pypi_requests as pypi

# Setup ArgumentParser
cmd_line_parser = argparse.ArgumentParser(description="Adabot utility for CircuitPython Libraries.",
                                          prog="Adabot CircuitPython Libraries Utility")
cmd_line_parser.add_argument("-o", "--output_file", help="Output log to the filename provided.",
                             metavar="<OUTPUT FILENAME>", dest="output_file")
cmd_line_parser.add_argument("-v", "--verbose", help="Set the level of verbosity printed to the command prompt."
                             " Zero is off; One is on (default).", type=int, default=1, dest="verbose", choices=[0,1])
cmd_line_parser.add_argument("-e", "--error_depth", help="Set the threshold for outputting an error list. Default is 5.",
                             dest="error_depth", type=int, default=5, metavar="n")
cmd_line_parser.add_argument("-t", "--token", help="Prompt for a GitHub token to use for activating Travis.",
                             dest="gh_token", action="store_true")

# Define constants for error strings to make checking against them more robust:
ERROR_ENABLE_TRAVIS = "Unable to enable Travis build"
ERROR_README_DOWNLOAD_FAILED = "Failed to download README"
ERROR_README_IMAGE_MISSING_ALT = "README image missing alt text"
ERROR_README_DUPLICATE_ALT_TEXT = "README has duplicate alt text"
ERROR_README_MISSING_DISCORD_BADGE = "README missing Discord badge"
ERROR_README_MISSING_RTD_BADGE = "README missing ReadTheDocs badge"
ERROR_README_MISSING_TRAVIS_BADGE = "README missing Travis badge"
ERROR_PYFILE_DOWNLOAD_FAILED = "Failed to download .py code file"
ERROR_PYFILE_MISSING_STRUCT = ".py file contains reference to import ustruct" \
" without reference to import struct.  See issue " \
"https://github.com/adafruit/circuitpython/issues/782"
ERROR_MISMATCHED_READTHEDOCS = "Mismatched readthedocs.yml"
ERROR_MISSING_EXAMPLE_FILES = "Missing .py files in examples folder"
ERROR_MISSING_EXAMPLE_FOLDER = "Missing examples folder"
ERROR_EXAMPLE_MISSING_SENSORNAME = "Example file(s) missing sensor/library name."
ERROR_MISSING_EXAMPLE_SIMPLETEST = "Missing simpletest example."
ERROR_MISSING_LIBRARIANS = "CircuitPythonLibrarians team missing or does not have write access."
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
ERROR_GITHUB_NO_RELEASE = "Library repository has no releases."
ERROR_GITHUB_COMMITS_SINCE_LAST_RELEASE = "Library has new commits since last release."
ERROR_RTD_MISSING_LATEST_RELEASE = "ReadTheDocs missing the latest release. (Ignore me! RTD doesn't update when a new version is released. Only on pushes.)"
ERROR_DRIVERS_PAGE_DOWNLOAD_FAILED = "Failed to download drivers page from CircuitPython docs"
ERROR_DRIVERS_PAGE_DOWNLOAD_MISSING_DRIVER = "CircuitPython drivers page missing driver"
ERROR_UNABLE_PULL_REPO_DIR = "Unable to pull repository directory"
ERROR_UNABLE_PULL_REPO_EXAMPLES = "Unable to pull repository examples files"
ERROR_NOT_ON_PYPI = "Not listed on PyPi for CPython use"
ERROR_PYLINT_VERSION_NOT_FIXED = "PyLint version not fixed"
ERROR_PYLINT_VERSION_VERY_OUTDATED = "PyLint version very out of date"
ERROR_PYLINT_VERSION_NOT_LATEST = "PyLint version not latest"
ERROR_NEW_REPO_IN_WORK = "New repo(s) currently in work, and unreleased."

# These are warnings or errors that sphinx generate that we're ok ignoring.
RTD_IGNORE_NOTICES = ("WARNING: html_static_path entry", "WARNING: nonlocal image URI found:")

# Constant for bundle repo name.
BUNDLE_REPO_NAME = "Adafruit_CircuitPython_Bundle"

# Repos to ignore for validation they exist in the bundle.  Add repos by their
# full name on Github (like Adafruit_CircuitPython_Bundle).
BUNDLE_IGNORE_LIST = [BUNDLE_REPO_NAME]

LIBRARY_DOESNT_NEED_BLINKA = "Adafruit_CircuitPython_ImageLoad"

# Cache CircuitPython's subprojects on ReadTheDocs so its not fetched every repo check.
rtd_subprojects = None

# Cache the CircuitPython driver page so we can make sure every driver is linked to.
core_driver_page = None

def parse_gitmodules(input_text):
    """Parse a .gitmodules file and return a list of all the git submodules
    defined inside of it.  Each list item is 2-tuple with:
      - submodule name (string)
      - submodule variables (dictionary with variables as keys and their values)
    The input should be a string of text with the complete representation of
    the .gitmodules file.

    See this for the format of the .gitmodules file, it follows the git config
    file format:
      https://www.kernel.org/pub/software/scm/git/docs/git-config.html

    Note although the format appears to be like a ConfigParser-readable ini file
    it is NOT possible to parse with Python's built-in ConfigParser module.  The
    use of tabs in the git config format breaks ConfigParser, and the subsection
    values in double quotes are completely lost.  A very basic regular
    expression-based parsing logic is used here to parse the data.  This parsing
    is far from perfect and does not handle escaping quotes, line continuations
    (when a line ends in '\;'), etc.  Unfortunately the git config format is
    surprisingly complex and no mature parsing modules are available (outside
    the code in git itself).
    """
    # Assume no results if invalid input.
    if input_text is None:
        return []
    # Define a regular expression to match a basic submodule section line and
    # capture its subsection value.
    submodule_section_re = '^\[submodule "(.+)"\]$'
    # Define a regular expression to match a variable setting line and capture
    # the variable name and value.  This does NOT handle multi-line or quote
    # escaping (far outside the abilities of a regular expression).
    variable_re = '^\s*([a-zA-Z0-9\-]+) =\s+(.+?)\s*$'
    # Process all the lines to parsing submodule sections and the variables
    # within them as they're found.
    results = []
    submodule_name = None
    submodule_variables = {}
    for line in input_text.splitlines():
        submodule_section_match = re.match(submodule_section_re, line, flags=re.IGNORECASE)
        variable_match = re.match(variable_re, line)
        if submodule_section_match:
            # Found a new section.  End the current one if it had data and add
            # it to the results, then start parsing a new section.
            if submodule_name is not None:
                results.append((submodule_name, submodule_variables))
            submodule_name = submodule_section_match.group(1)
            submodule_variables = {}
        elif variable_match:
            # Found a variable, add it to the current section variables.
            # Force the variable name to lower case as variable names are
            # case-insensitive in git config sections and this makes later
            # processing easier (can assume lower-case names to find values).
            submodule_variables[variable_match.group(1).lower()] = variable_match.group(2)
    # Add the last parsed section if it exists.
    if submodule_name is not None:
        results.append((submodule_name, submodule_variables))
    return results

def get_bundle_submodules():
    """Query Adafruit_CircuitPython_Bundle repository for all the submodules
    (i.e. modules included inside) and return a list of the found submodules.
    Each list item is a 2-tuple of submodule name and a dict of submodule
    variables including 'path' (location of submodule in bundle) and
    'url' (URL to git repository with submodule contents).
    """
    # Assume the bundle repository is public and get the .gitmodules file
    # without any authentication or Github API usage.  Also assumes the
    # master branch of the bundle is the canonical source of the bundle release.
    result = requests.get('https://raw.githubusercontent.com/adafruit/Adafruit_CircuitPython_Bundle/master/.gitmodules',
                          timeout=15)
    if result.status_code != 200:
        output_handler("Failed to access bundle .gitmodules file from GitHub!", quiet=True)
        raise RuntimeError('Failed to access bundle .gitmodules file from GitHub!')
    return parse_gitmodules(result.text)

def sanitize_url(url):
    """Convert a Github repository URL into a format which can be compared for
    equality with simple string comparison.  Will strip out any leading URL
    scheme, set consistent casing, and remove any optional .git suffix.  The
    attempt is to turn a URL from Github (which can be one of many different
    schemes with and without suffxes) into canonical values for easy comparison.
    """
    # Make the url lower case to perform case-insensitive comparisons.
    # This might not actually be correct if Github cares about case (assumption
    # is no Github does not, but this is unverified).
    url = url.lower()
    # Strip out any preceding http://, https:// or git:// from the URL to
    # make URL comparisons safe (probably better to explicitly parse using
    # a URL module in the future).
    scheme_end = url.find('://')
    if scheme_end >= 0:
        url = url[scheme_end:]
    # Strip out any .git suffix if it exists.
    if url.endswith('.git'):
        url = url[:-4]
    return url

def is_repo_in_bundle(repo_clone_url, bundle_submodules):
    """Return a boolean indicating if the specified repository (the clone URL
    as a string) is in the bundle.  Specify bundle_submodules as a dictionary
    of bundle submodule state returned by get_bundle_submodules.
    """
    # Sanitize url for easy comparison.
    repo_clone_url = sanitize_url(repo_clone_url)
    # Search all the bundle submodules for any that have a URL which matches
    # this clone URL.  Not the most efficient search but it's a handful of
    # items in the bundle.
    for submodule in bundle_submodules:
        name, variables = submodule
        submodule_url = variables.get('url', '')
        # Compare URLs and skip to the next submodule if it's not a match.
        # Right now this is a case sensitive compare, but perhaps it should
        # be insensitive in the future (unsure if Github repos are sensitive).
        if repo_clone_url != sanitize_url(submodule_url):
            continue
        # URLs matched so now check if the submodule is placed in the libraries
        # subfolder of the bundle.  Just look at the path from the submodule
        # state.
        if variables.get('path', '').startswith('libraries/'):
            # Success! Found the repo as a submodule of the libraries folder
            # in the bundle.
            return True
    # Failed to find the repo as a submodule of the libraries folders.
    return False

def list_repos():
    """Return a list of all Adafruit repositories that start with
    Adafruit_CircuitPython.  Each list item is a dictionary of GitHub API
    repository state.
    """
    repos = []
    result = github.get("/search/repositories",
                        params={"q":"Adafruit_CircuitPython in:name fork:true",
                                "per_page": 100,
                                "sort": "updated",
                                "order": "asc"},
                        timeout=15)
    while result.ok:
        links = result.headers["Link"]
        #repos.extend(result.json()["items"]) # uncomment and comment below, to include all forks
        repos.extend(repo for repo in result.json()["items"] if (repo["owner"]["login"] == "adafruit" and
                     (repo["name"].startswith("Adafruit_CircuitPython") or repo["name"] == "circuitpython")))

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

def validate_repo_state(repo):
    """Validate a repository meets current CircuitPython criteria.  Expects
    a dictionary with a GitHub API repository state (like from the list_repos
    function).  Returns a list of string error messages for the repository.
    """
    global bundle_submodules
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
    if not is_repo_in_bundle(full_repo["clone_url"], bundle_submodules) and \
       not repo["name"] in BUNDLE_IGNORE_LIST:  # Don't assume the bundle will
                                                # bundle itself and possibly
                                                # other repos.
        errors.append(ERROR_NOT_IN_BUNDLE)
    if "allow_squash_merge" not in full_repo or full_repo["allow_squash_merge"] or full_repo["allow_rebase_merge"]:
        errors.append(ERROR_ONLY_ALLOW_MERGES)
    return errors

def validate_release_state(repo):
    """Validate if a repo 1) has a release, and 2) if there have been commits
    since the last release. Returns a list of string error messages for the
    repository.
    """
    if not (repo["owner"]["login"] == "adafruit" and
            repo["name"].startswith("Adafruit_CircuitPython")):
        return []

    if repo["name"] in BUNDLE_IGNORE_LIST:
        return []

    repo_last_release = github.get("/repos/" + repo["full_name"] + "/releases/latest")
    if not repo_last_release.ok:
        return [ERROR_GITHUB_NO_RELEASE]
    repo_release_json = repo_last_release.json()
    if "tag_name" in repo_release_json:
        tag_name = repo_release_json["tag_name"]
    elif "message" in repo_release_json:
        if repo_release_json["message"] == "Not Found":
            return [ERROR_GITHUB_NO_RELEASE]
        else:
            output_handler("Error: retrieving latest release information failed on '{0}'. Information Received: {1}".format(
                           repo["name"], repo_release_json["message"]))
            return []

    compare_tags = github.get("/repos/" + repo["full_name"] + "/compare/master..." + tag_name)
    if not compare_tags.ok:
        output_handler("Error: failed to compare {0} 'master' to tag '{1}'".format(repo["name"], tag_name))
        return []
    compare_tags_json = compare_tags.json()
    if "status" in compare_tags_json:
        if compare_tags.json()["status"] != "identical":
            #print("Compare {4} status: {0} \n  Ahead: {1} \t Behind: {2} \t Commits: {3}".format(
            #      compare_tags_json["status"], compare_tags_json["ahead_by"],
            #      compare_tags_json["behind_by"], compare_tags_json["total_commits"], repo["full_name"]))
            return [ERROR_GITHUB_COMMITS_SINCE_LAST_RELEASE]
    elif "errors" in compare_tags_json:
        output_handler("Error: comparing latest release to 'master' failed on '{0}'. Error Message: {1}".format(
                       repo["name"], compare_tags_json["message"]))

    return []

def validate_readme(repo, download_url):
    # We use requests because file contents are hosted by githubusercontent.com, not the API domain.
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
        errors.append(ERROR_README_MISSING_TRAVIS_BADGE)

    return errors

def validate_py_for_ustruct(repo, download_url):
    """ For a .py file, look for usage of "import ustruct" and
        look for "import struct".  If the "import ustruct" is
        used with NO "import struct" generate an error.
    """
    # We use requests because file contents are hosted by githubusercontent.com, not the API domain.
    contents = requests.get(download_url, timeout=30)
    if not contents.ok:
        return [ERROR_PYFILE_DOWNLOAD_FAILED]

    errors = []

    lines = contents.text.split("\n")
    ustruct_lines = [l for l in lines if re.match(r"[\s]*import[\s][\s]*ustruct", l)]
    struct_lines = [l for l in lines if re.match(r"[\s]*import[\s][\s]*struct", l)]
    if ustruct_lines and not struct_lines:
        errors.append(ERROR_PYFILE_MISSING_STRUCT)

    return errors

def validate_travis_yml(repo, travis_yml_file_info):
    """Check size and then check pypi compatibility.
    """
    download_url = travis_yml_file_info["download_url"]
    contents = requests.get(download_url, timeout=30)
    if not contents.ok:
        return [ERROR_PYFILE_DOWNLOAD_FAILED]

    errors = []

    lines = contents.text.split("\n")
    pypi_providers_lines = [l for l in lines if re.match(r"[\s]*-[\s]*provider:[\s]*pypi[\s]*", l)]

    if not pypi_providers_lines:
        errors.append(ERROR_MISSING_PYPIPROVIDER)

    pylint_version = None
    for line in lines:
        if not line.strip().startswith("- pip install --force-reinstall pylint=="):
            continue
        pylint_version = line.split("=")[-1]

    if not pylint_version:
        errors.append(ERROR_PYLINT_VERSION_NOT_FIXED)
    elif pylint_version.startswith("1."):
        errors.append(ERROR_PYLINT_VERSION_VERY_OUTDATED)
    elif pylint_version != latest_pylint:
        errors.append(ERROR_PYLINT_VERSION_NOT_LATEST)

    return errors

def validate_setup_py(repo, file_info):
    """Check setup.py for pypi compatibility
    """
    download_url = file_info["download_url"]
    contents = requests.get(download_url, timeout=30)
    if not contents.ok:
        return [ERROR_PYFILE_DOWNLOAD_FAILED]

    errors = []


    return errors

def validate_requirements_txt(repo, file_info):
    """Check requirements.txt for pypi compatibility
    """
    download_url = file_info["download_url"]
    contents = requests.get(download_url, timeout=30)
    if not contents.ok:
        return [ERROR_PYFILE_DOWNLOAD_FAILED]

    errors = []
    lines = contents.text.split("\n")
    blinka_lines = [l for l in lines if re.match(r"[\s]*Adafruit-Blinka[\s]*", l)]

    if not blinka_lines and repo["name"] not in LIBRARY_DOESNT_NEED_BLINKA:
        errors.append(ERROR_MISSING_BLINKA)
    return errors

def validate_contents(repo):
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
    if not content_list.ok:
        return [ERROR_UNABLE_PULL_REPO_CONTENTS]

    content_list = content_list.json()
    files = [x["name"] for x in content_list]

    # ignore new/in-work repos, which should have less than 8 files:
    # ___.py or folder, CoC, .travis.yml, .readthedocs.yml, docs/, examples/, README, LICENSE
    if len(files) < 8:
        BUNDLE_IGNORE_LIST.append(repo["name"])
        return [ERROR_NEW_REPO_IN_WORK]

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
        errors.extend(validate_readme(repo, readme_info["download_url"]))

    if ".travis.yml" in files:
        file_info = content_list[files.index(".travis.yml")]
        errors.extend(validate_travis_yml(repo, file_info))
    else:
        errors.append(ERROR_MISSING_TRAVIS_CONFIG)

    if "readthedocs.yml" in files or ".readthedocs.yml" in files:
        fn = "readthedocs.yml"
        if ".readthedocs.yml" in files:
            fn = ".readthedocs.yml"
        file_info = content_list[files.index(fn)]
        if file_info["sha"] != "f4243ad548bc5e4431f2d3c5d486f6c9c863888b":
            errors.append(ERROR_MISMATCHED_READTHEDOCS)
    else:
        errors.append(ERROR_MISSING_READTHEDOCS)

    if "setup.py" in files:
        file_info = content_list[files.index("setup.py")]
        errors.extend(validate_setup_py(repo, file_info))
    else:
        errors.append(ERROR_MISSING_SETUP_PY)

    if "requirements.txt" in files:
        file_info = content_list[files.index("requirements.txt")]
        errors.extend(validate_requirements_txt(repo, file_info))
    else:
        errors.append(ERROR_MISSING_REQUIREMENTS_TXT)


    #Check for an examples folder.
    dirs = [x["name"] for x in content_list if x["type"] == "dir"]
    if "examples" in dirs:
        # check for at least on .py file
        examples_list = github.get("/repos/" + repo["full_name"] + "/contents/examples")
        if not examples_list.ok:
            errors.append(ERROR_UNABLE_PULL_REPO_EXAMPLES)
        examples_list = examples_list.json()
        if len(examples_list) < 1:
            errors.append(ERROR_MISSING_EXAMPLE_FILES)
        else:
            lib_name = repo["name"][repo["name"].rfind("_") + 1:].lower()
            all_have_name = True
            simpletest_exists = False
            for example in examples_list:
                if not example["name"].lower().startswith(lib_name):
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
    pyfiles = [x["download_url"] for x in content_list if re_str.fullmatch(x["name"])]
    for pyfile in pyfiles:
        # adafruit_xxx.py file; check if for proper usage of ustruct
        errors.extend(validate_py_for_ustruct(repo, pyfile))

    # now location any directories whose names begin with "adafruit_"
    re_str = re.compile('adafruit\_[\w]*')
    for adir in dirs:
        if re_str.fullmatch(adir):
            # retrieve the files in that directory
            dir_file_list = github.get("/repos/" + repo["full_name"] + "/contents/" + adir)
            if not dir_file_list.ok:
                errors.append(ERROR_UNABLE_PULL_REPO_DIR)
            dir_file_list = dir_file_list.json()
            # search for .py files in that directory
            dir_files = [x["download_url"] for x in dir_file_list if x["type"] == "file" and x["name"].endswith(".py")]
            for dir_file in dir_files:
                # .py files in subdirectory adafruit_xxx; check if for proper usage of ustruct
                errors.extend(validate_py_for_ustruct(repo, dir_file))

    return errors

def validate_travis(repo):
    """Validate and configure a repository has the expected state in Travis
    CI.  This will both check Travis state and attempt to enable Travis CI
    and setup the expected state in Travis if not enabled.  Expects a
    dictionary with a GitHub API repository state (like from the list_repos
    function).  Returns a list of string error messages for the repository.
    """
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
            #output_handler(activate.request.url)
            #output_handler("{} {}".format(activate, activate.text))
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
        if not github_token:
            return [ERROR_TRAVIS_GITHUB_TOKEN]
        else:
            global full_auth
            if not full_auth:
                #github_user = github_token
                github_user = github.get("/user").json()
                password = input("Password for " + github_user["login"] + ": ")
                full_auth = (github_user["login"], password.strip())
            if not full_auth:
                return [ERROR_TRAVIS_GITHUB_TOKEN]

            new_access_token = {"scopes": ["public_repo"],
                                "note": "TravisCI release token for " + repo["full_name"],
                                "note_url": "https://travis-ci.org/" + repo["full_name"]}
            token = github.post("/authorizations", json=new_access_token, auth=full_auth)
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
                github.delete("/authorizations/{}".format(grant_id), auth=full_auth)
                return [ERROR_TRAVIS_GITHUB_TOKEN]

    return []

def validate_readthedocs(repo):
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
            rtd_subprojects[sanitize_url(subproject["repo"])] = subproject

    repo_url = sanitize_url(repo["clone_url"])
    if repo_url not in rtd_subprojects:
        return [ERROR_RTD_SUBPROJECT_MISSING]

    errors = []
    subproject = rtd_subprojects[repo_url]

    if 105398 not in subproject["users"]:
        errors.append(ERROR_RTD_ADABOT_MISSING)

    valid_versions = requests.get(
        "https://readthedocs.org/api/v2/project/{}/valid_versions/".format(subproject["id"]),
        timeout=15)
    if not valid_versions.ok:
        errors.append(ERROR_RTD_VALID_VERSIONS_FAILED)
    else:
        valid_versions = valid_versions.json()
        latest_release = github.get("/repos/{}/releases/latest".format(repo["full_name"]))
        if not latest_release.ok:
            errors.append(ERROR_GITHUB_RELEASE_FAILED)
        else:
            if latest_release.json()["tag_name"] not in valid_versions["flat"]:
                errors.append(ERROR_RTD_MISSING_LATEST_RELEASE)

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

def validate_core_driver_page(repo):
    if not (repo["owner"]["login"] == "adafruit" and
            repo["name"].startswith("Adafruit_CircuitPython")):
        return []
    if repo["name"] in BUNDLE_IGNORE_LIST:
        return []
    global core_driver_page
    if not core_driver_page:
        driver_page = requests.get("https://raw.githubusercontent.com/adafruit/circuitpython/master/docs/drivers.rst",
                                   timeout=15)
        if not driver_page.ok:
            return [ERROR_DRIVERS_PAGE_DOWNLOAD_FAILED]
        core_driver_page = driver_page.text

    repo_short_name = repo["name"][len("Adafruit_CircuitPython_"):].lower()
    if "https://circuitpython.readthedocs.io/projects/" + repo_short_name + "/en/latest/" not in core_driver_page:
        return [ERROR_DRIVERS_PAGE_DOWNLOAD_MISSING_DRIVER]
    return []

def validate_repo(repo):
    """Run all the current validation functions on the provided repository and
    return their results as a list of string errors.
    """
    errors = []
    for validator in validators:
        errors.extend(validator(repo))
    return errors

def gather_insights(repo, insights, since):
    """Gather analytics about a repository like open and merged pull requests.
    This expects a dictionary with GitHub API repository state (like from the
    list_repos function) and will fill in the provided insights dictionary
    with analytics it computes for the repository.
    """
    if repo["owner"]["login"] != "adafruit":
        return
    params = {"sort": "updated",
              "state": "all",
              "since": str(since)}
    response = github.get("/repos/" + repo["full_name"] + "/issues", params=params)
    if not response.ok:
        output_handler("Insights request failed: {}".format(repo["full_name"]))
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

    params = {"state": "open", "per_page": 100}
    response = github.get("/repos/" + repo["full_name"] + "/issues", params=params)
    if not response.ok:
        output_handler("Issues request failed: {}".format(repo["full_name"]))
    issues = response.json()
    for issue in issues:
        created = datetime.datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ")
        if "pull_request" in issue:
            insights["open_prs"].append(issue["pull_request"]["html_url"])
        else:
            insights["open_issues"].append(issue["html_url"])

def repo_is_on_pypi(repo):
    """returns True when the provided repository is in pypi"""
    is_on = False
    the_page = pypi.get("/pypi/"+repo["name"]+"/json")
    if the_page and the_page.status_code == 200:
        is_on = True

    return is_on

def validate_in_pypi(repo):
    """prints a list of Adafruit_CircuitPython libraries that are in pypi"""
    if repo["name"] in BUNDLE_IGNORE_LIST:
        return []
    if not (repo["owner"]["login"] == "adafruit" and
            repo["name"].startswith("Adafruit_CircuitPython")):
        return []
    if not repo_is_on_pypi(repo):
        return [ERROR_NOT_ON_PYPI]
    return []

def run_library_checks():
    """runs the various library checking functions"""
    pylint_info = pypi.get("/pypi/pylint/json")
    if pylint_info and pylint_info.ok:
        latest_pylint = pylint_info.json()["info"]["version"]
    output_handler("Latest pylint is: {}".format(latest_pylint))

    repos = list_repos()
    output_handler("Found {} repos to check.".format(len(repos)))
    global bundle_submodules
    bundle_submodules = get_bundle_submodules()
    output_handler("Found {} submodules in the bundle.".format(len(bundle_submodules)))
    github_user = github.get("/user").json()
    output_handler("Running GitHub checks as " + github_user["login"])
    travis_user = travis.get("/user").json()
    output_handler("Running Travis checks as " + travis_user["login"])
    need_work = 0
    lib_insights = {
        "merged_prs": 0,
        "closed_prs": 0,
        "new_prs": 0,
        "active_prs": 0,
        "open_prs": [],
        "pr_authors": set(),
        "pr_merged_authors": set(),
        "pr_reviewers": set(),
        "closed_issues": 0,
        "new_issues": 0,
        "active_issues": 0,
        "open_issues": [],
        "issue_authors": set(),
        "issue_closers": set(),
    }
    core_insights = copy.deepcopy(lib_insights)
    for k in core_insights:
        if isinstance(core_insights[k], set):
            core_insights[k] = set()
        if isinstance(core_insights[k], list):
            core_insights[k] = []
    repo_needs_work = []
    since = datetime.datetime.now() - datetime.timedelta(days=7)
    repos_by_error = {}

    for repo in repos:
        errors = validate_repo(repo)
        if errors:
            need_work += 1
            repo_needs_work.append(repo)
            # print(repo["full_name"])
            # print("\n".join(errors))
            # print()
        for error in errors:
            if error not in repos_by_error:
                repos_by_error[error] = []
            repos_by_error[error].append(repo["html_url"])
        insights = lib_insights
        if repo["name"] == "circuitpython" and repo["owner"]["login"] == "adafruit":
            insights = core_insights
        gather_insights(repo, insights, since)

    output_handler()
    output_handler("State of CircuitPython + Libraries")

    output_handler("Overall")
    print_pr_overview(lib_insights, core_insights)
    print_issue_overview(lib_insights, core_insights)

    output_handler()
    output_handler("Core")
    print_pr_overview(core_insights)
    output_handler("* {} open pull requests".format(len(core_insights["open_prs"])))
    for pr in core_insights["open_prs"]:
        output_handler("  * {}".format(pr))
    print_issue_overview(core_insights)
    output_handler("* {} open issues".format(len(insights["open_issues"])))
    output_handler("  * https://github.com/adafruit/circuitpython/issues")
    output_handler()
    print_circuitpython_download_stats()

    output_handler()
    output_handler("Libraries")
    print_pr_overview(lib_insights)
    output_handler("* {} open pull requests".format(len(lib_insights["open_prs"])))
    for pr in lib_insights["open_prs"]:
        output_handler("  * {}".format(pr))
    print_issue_overview(lib_insights)
    output_handler("* {} open issues".format(len(lib_insights["open_issues"])))
    for issue in lib_insights["open_issues"]:
        output_handler("  * {}".format(issue))

    lib_repos = []
    for repo in repos:
        if repo["owner"]["login"] == "adafruit" and repo["name"].startswith("Adafruit_CircuitPython"):
            lib_repos.append(repo)

    # print("- [ ] [{0}](https://github.com/{1})".format(repo["name"], repo["full_name"]))
    output_handler("{} out of {} repos need work.".format(need_work, len(lib_repos)))

    list_repos_for_errors = [ERROR_NOT_IN_BUNDLE]
    output_handler()
    for error in repos_by_error:
        if not repos_by_error[error]:
            continue
        output_handler()
        error_count = len(repos_by_error[error])
        output_handler("{} - {}".format(error, error_count))
        if error_count <= error_depth or error in list_repos_for_errors:
            output_handler("\n".join(["  * " + x for x in repos_by_error[error]]))

def output_handler(message="", quiet=False):
    """Handles message output to prompt/file for print_*() functions."""
    if output_filename is not None:
        file_data.append(message)
    if verbosity and not quiet:
        print(message)

def print_circuitpython_download_stats():
    """Gather and report analytics on the main CircuitPython repository."""
    response = github.get("/repos/adafruit/circuitpython/releases")
    if not response.ok:
        output_handler("Core CircuitPython GitHub analytics request failed.")
    releases = response.json()
    found_unstable = False
    found_stable = False
    for release in releases:
        published = datetime.datetime.strptime(release["published_at"], "%Y-%m-%dT%H:%M:%SZ")
        if not found_unstable and not release["draft"] and release["prerelease"]:
            found_unstable = True
        elif not found_stable and not release["draft"] and not release["prerelease"]:
            found_stable = True
        else:
            continue

        by_board = {}
        by_language = {}
        by_both = {}
        total = 0
        for asset in release["assets"]:
            if not asset["name"].startswith("adafruit-circuitpython"):
                continue
            count = asset["download_count"]
            parts = asset["name"].split("-")
            board = parts[2]
            language = "en_US"
            if len(parts) == 6:
                language = parts[3]
            if language not in by_language:
                by_language[language] = 0
            by_language[language] += count
            if board not in by_board:
                by_board[board] = 0
                by_both[board] = {}
            by_board[board] += count
            by_both[board][language] = count

            total += count
        output_handler("Download stats for {}".format(release["tag_name"]))
        output_handler("{} total".format(total))
        output_handler()
        output_handler("By board:")
        for board in by_board:
            output_handler("* {} - {}".format(board, by_board[board]))
        output_handler()
        output_handler("By language:")
        for language in by_language:
            output_handler("* {} - {}".format(language, by_language[language]))
        output_handler()

def print_pr_overview(*insights):
    merged_prs = sum([x["merged_prs"] for x in insights])
    authors = set().union(*[x["pr_merged_authors"] for x in insights])
    reviewers = set().union(*[x["pr_reviewers"] for x in insights])

    output_handler("* {} pull requests merged".format(merged_prs))
    output_handler("  * {} authors - {}".format(len(authors), ", ".join(authors)))
    output_handler("  * {} reviewers - {}".format(len(reviewers), ", ".join(reviewers)))

def print_issue_overview(*insights):
    closed_issues = sum([x["closed_issues"] for x in insights])
    issue_closers = set().union(*[x["issue_closers"] for x in insights])
    new_issues = sum([x["new_issues"] for x in insights])
    issue_authors = set().union(*[x["issue_authors"] for x in insights])
    output_handler("* {} closed issues by {} people, {} opened by {} people"
                   .format(closed_issues, len(issue_closers),
                   new_issues, len(issue_authors)))


# Define global state shared by the functions above:
# Github authentication password/token.  Used to generate new tokens.
full_auth = None
# Functions to run on repositories to validate their state.  By convention these
# return a list of string errors for the specified repository (a dictionary
# of Github API repository object state).
validators = [validate_contents, validate_repo_state, validate_travis, validate_readthedocs,
              validate_core_driver_page, validate_in_pypi, validate_release_state]
# Submodules inside the bundle (result of get_bundle_submodules)
bundle_submodules = []

# Load the latest pylint version
latest_pylint = "2.0.1"

# Logging output filename and data
output_filename = None
file_data = []
# Verbosity level
verbosity = 1
github_token = False

if __name__ == "__main__":
    cmd_line_args = cmd_line_parser.parse_args()
    error_depth = cmd_line_args.error_depth
    verbosity = cmd_line_args.verbose
    github_token = cmd_line_args.gh_token
    if cmd_line_args.output_file:
        output_filename = cmd_line_args.output_file

    try:
        run_library_checks()
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
