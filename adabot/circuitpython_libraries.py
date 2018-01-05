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
import sys

import requests

from adabot import github_requests as github
from adabot import travis_requests as travis


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

def list_repos():
    repos = []
    result = github.get("/search/repositories",
                        params={"q":"Adafruit_CircuitPython in:name fork:true",
                                "per_page": 100,
                                "sort": "updated",
                                "order": "asc"})
    while result.ok:
        links = result.headers["Link"]
        repos.extend(result.json()["items"])
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
        result = requests.get(link)

    return repos

def validate_repo(repo):
    if not (repo["owner"]["login"] == "adafruit" and
            repo["name"].startswith("Adafruit_CircuitPython")):
        return []
    full_repo = github.get("/repos/" + repo["full_name"])
    if not full_repo.ok:
        return ["Unable to pull repo details"]
    errors = []
    if repo["has_wiki"]:
        errors.append("Wiki should be disabled")
    if not repo["license"]:
        errors.append("Missing license.")
    if not repo["permissions"]["push"]:
        errors.append("Likely missing CircuitPythonLibrarians team.")
    return errors

def validate_contents(repo):
    if not (repo["owner"]["login"] == "adafruit" and
            repo["name"].startswith("Adafruit_CircuitPython")):
        return []
    if repo["name"] == "Adafruit_CircuitPython_Bundle":
        return []

    content_list = github.get("/repos/" + repo["full_name"] + "/contents/")
    if not content_list.ok:
        return ["Unable to pull repo contents"]

    content_list = content_list.json()
    files = [x["name"] for x in content_list]

    errors = []
    if ".pylintrc" not in files:
        errors.append("Missing lint config")

    if ".travis.yml" in files:
        file_info = content_list[files.index(".travis.yml")]
        if file_info["size"] > 1000:
            errors.append("Old travis config")
    else:
        errors.append("Missing .travis.yml")

    if "readthedocs.yml" in files:
        file_info = content_list[files.index("readthedocs.yml")]
        if file_info["sha"] != "f4243ad548bc5e4431f2d3c5d486f6c9c863888b":
            errors.append("Mismatched readthedocs.yml")
    else:
        errors.append("Missing readthedocs.yml")

    #Check for an examples folder.
    dirs = [x["name"] for x in content_list if x["type"] == "dir"]
    if "examples" in dirs:
        # check for at least on .py file
        examples_list = github.get("/repos/" + repo["full_name"] + "/contents/examples")
        if not examples_list.ok:
            errors.append("Unable to retrieve examples folder contents")
        examples_list = examples_list.json()
        examples_files = [x["name"] for x in examples_list if x["type"] == "file" and x["name"].endswith(".py")]
        if not examples_files:
            errors.append("Missing .py files in examples folder")
    else:
        errors.append("Missing examples folder")

    return errors

full_auth = None

def validate_travis(repo):
    if not (repo["owner"]["login"] == "adafruit" and
            repo["name"].startswith("Adafruit_CircuitPython")):
        return []
    repo_url = "/repo/" + repo["owner"]["login"] + "%2F" + repo["name"]
    result = travis.get(repo_url)
    if not result.ok:
        #print(result, result.request.url, result.request.headers)
        #print(result.text)
        return ["Travis error with repo:", repo["full_name"]]
    result = result.json()
    if not result["active"]:
        activate = travis.post(repo_url + "/activate")
        if not activate.ok:
            print(activate.request.url)
            print(activate, activate.text)
            return ["Unable to enable Travis build"]

    env_variables = travis.get(repo_url + "/env_vars")
    if not env_variables.ok:
        #print(env_variables, env_variables.text)
        #print(env_variables.request.headers)
        return ["Unable to read Travis env variables"]
    env_variables = env_variables.json()
    found_token = False
    for var in env_variables["env_vars"]:
        found_token = found_token or var["name"] == "GITHUB_TOKEN"
    ok = True
    if not found_token:
        global full_auth
        if not full_auth:
            github_user = github.get("/user").json()
            password = input("Password for " + github_user["login"] + ": ")
            full_auth = (github_user["login"], password.strip())
        if not full_auth:
            return ["Unable to find or create (no auth) GITHUB_TOKEN env variable"]

        new_access_token = {"scopes": ["public_repo"],
                            "note": "TravisCI release token for " + repo["full_name"],
                            "note_url": "https://travis-ci.org/" + repo["full_name"]}
        token = github.post("/authorizations", json=new_access_token, auth=full_auth)
        if not token.ok:
            print(token.text)
            return ["Token creation failed"]

        token = token.json()["token"]

        new_var = {"env_var.name": "GITHUB_TOKEN",
                   "env_var.value": token,
                   "env_var.public": False}
        new_var_result = travis.post(repo_url + "/env_vars", json=new_var)
        if not new_var_result.ok:
            #print(new_var_result.headers, new_var_result.text)
            return ["Unable to find or create GITHUB_TOKEN env variable"]
    return []

validators = [validate_repo, validate_travis, validate_contents]

def validate_repo(repo):
    errors = []
    for validator in validators:
        errors.extend(validator(repo))
    return errors

def gather_insights(repo, insights, since):
    if repo["owner"]["login"] != "adafruit":
        return
    params = {"sort": "updated",
              "state": "all",
              "since": str(since)}
    response = github.get("/repos/" + repo["full_name"] + "/issues", params=params)
    if not response.ok:
        print("request failed")
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
        print("request failed")
    issues = response.json()
    for issue in issues:
        created = datetime.datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ")
        if "pull_request" in issue:
            insights["open_prs"].append(issue["pull_request"]["html_url"])
        else:
            insights["open_issues"].append(issue["html_url"])

def print_circuitpython_download_stats():
    response = github.get("/repos/adafruit/circuitpython/releases")
    if not response.ok:
        print("request failed")
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

        print("Download stats for {}".format(release["tag_name"]))
        total = 0
        for asset in release["assets"]:
            if not asset["name"].startswith("adafruit-circuitpython"):
                continue
            board = asset["name"].split("-")[2]
            print("* {} - {}".format(board, asset["download_count"]))
            total += asset["download_count"]
        print("{} total".format(total))

if __name__ == "__main__":
    repos = list_repos()
    print("Found {} repos to check.".format(len(repos)))
    github_user = github.get("/user").json()
    print("Running GitHub checks as " + github_user["login"])
    travis_user = travis.get("/user").json()
    print("Running Travis checks as " + travis_user["login"])
    need_work = 0
    insights = {
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
        gather_insights(repo, insights, since)
    circuitpython_repo = github.get("/repos/adafruit/circuitpython").json()
    gather_insights(circuitpython_repo, insights, since)
    print("State of CircuitPython + Libraries")
    print("* {} pull requests merged".format(insights["merged_prs"]))
    authors = insights["pr_merged_authors"]
    print("  * {} authors - {}".format(len(authors), ", ".join(authors)))
    reviewers = insights["pr_reviewers"]
    print("  * {} reviewers - {}".format(len(reviewers), ", ".join(reviewers)))
    new_authors = insights["pr_authors"]
    print("* {} new PRs, {} authors - {}".format(insights["new_prs"], len(new_authors), ", ".join(new_authors)))
    print("* {} closed issues by {} people, {} opened by {} people"
          .format(insights["closed_issues"], len(insights["issue_closers"]),
                  insights["new_issues"], len(insights["issue_authors"])))
    print("* {} open pull requests".format(len(insights["open_prs"])))
    for pr in insights["open_prs"]:
        print("  * {}".format(pr))
    print("* {} open issues".format(len(insights["open_issues"])))
    for issue in insights["open_issues"]:
        print("  * {}".format(issue))
    print_circuitpython_download_stats()
    # print("- [ ] [{0}](https://github.com/{1})".format(repo["name"], repo["full_name"]))
    print("{} out of {} repos need work.".format(need_work, len(repos)))

    list_repos_for_errors = ["Wiki should be disabled", "Likely missing CircuitPythonLibrarians team.", "Unable to enable Travis build"]
    for error in repos_by_error:
        if len(repos_by_error[error]) == 0:
            continue
        print()
        print(error, "- {}".format(len(repos_by_error[error])))
        if error in list_repos_for_errors:
            print("\n".join(repos_by_error[error]))
