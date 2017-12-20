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

from adabot import github_requests as github
from adabot import travis_requests as travis
import sys
import datetime

def list_repos():
    result = github.get("/search/repositories",
                        params={"q":"Adafruit_CircuitPython in:name",
                                "per_page": 100,
                                "sort": "updated",
                                "order": "asc"})
    result = result.json()
    if result["total_count"] > len(result["items"]):
        print("Implement pagination of results!!!")
    return result["items"]

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
    files = [x["name"] for x in content_list if x["type"] == "file"]

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
            #print(activate, activate.text)
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
            #print(token.text)
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
        "pr_authors": set(),
        "pr_merged_authors": set(),
        "pr_reviewers": set(),
        "closed_issues": 0,
        "new_issues": 0,
        "active_issues": 0,
        "issue_authors": set(),
        "issue_closers": set(),
    }
    repo_needs_work = []
    since = datetime.datetime.now() - datetime.timedelta(days=7)
    for repo in repos:
        errors = []
        prs = github.get("/repos/" + repo["full_name"] + "/pulls")
        if prs.ok:
            lint_pr_title = "Update to new build process and turn on lint."
            if any([pr["title"] == lint_pr_title for pr in prs.json()]):
                errors.append("Pending PR")
        errors.extend(validate_repo(repo))
        if errors:
            need_work += 1
            repo_needs_work.append(repo)
            #print("\n".join(errors))
            #print()
        gather_insights(repo, insights, since)
    circuitpython_repo = github.get("/repos/adafruit/circuitpython").json()
    gather_insights(circuitpython_repo, insights, since)
    print(insights)
    # print("- [ ] [{0}](https://github.com/{1})".format(repo["name"], repo["full_name"]))
    print("{} out of {} repos need work.".format(need_work, len(repos)))
