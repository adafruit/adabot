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

def list_repos():
    result = github.get("/search/repositories",
                        params={"q":"Adafruit_CircuitPython in:name",
                                "per_page": 100})
    result = result.json()
    if result["total_count"] > len(result["items"]):
        print("Implement pagination of results!!!")
    return result["items"]

def validate_repo(repo):
    if not (repo["owner"]["login"] == "adafruit" and
            repo["name"].startswith("Adafruit_CircuitPython")):
        return True
    full_repo = github.get("/repos/" + repo["full_name"])
    if not full_repo.ok:
        print("Unable to pull repo details")
        return False
    ok = True
    if repo["has_wiki"]:
        print("Wiki should be disabled " + repo["full_name"])
        ok = False
    if not repo["license"]:
        print(repo["full_name"], "missing license.")
        ok = False
    if not repo["permissions"]["push"]:
        print(repo["full_name"], "likely missing CircuitPythonLibrarians team.")
        ok = False
    return ok

def validate_travis(repo):
    if not (repo["owner"]["login"] == "adafruit" and
            repo["name"].startswith("Adafruit_CircuitPython")):
        return True
    repo_url = "/repo/" + repo["owner"]["login"] + "%2F" + repo["name"]
    result = travis.get(repo_url)
    if not result.ok:
        print(result, result.request.url, result.request.headers)
        print(result.text)
        print("Travis error with repo:", repo["full_name"])
        return False
    result = result.json()
    if not result["active"]:
        activate = travis.post(repo_url + "/activate")
        if not activate.ok:
            print(activate, activate.text)
            print("Unable to enable Travis build for " + repo["full_name"])
            return False

    env_variables = travis.get(repo_url + "/env_vars")
    if not env_variables.ok:
        print(env_variables, env_variables.text)
        print(env_variables.request.headers)
        print("Unable to read Travis env variables for " + repo["full_name"])
        return False
    env_variables = env_variables.json()
    found_token = False
    for var in env_variables["env_vars"]:
        found_token = found_token or var["name"] == "GITHUB_TOKEN"
    if not found_token:
        print("Unable to find GITHUB_TOKEN env variable for " + repo["full_name"])
        return False

validators = [validate_repo, validate_travis]

def validate_repo(repo):
    ok = True
    for validator in validators:
        ok = validator(repo) and ok
    return ok

if __name__ == "__main__":
    repos = list_repos()
    print("Found {} repos to check.".format(len(repos)))
    github_user = github.get("/user").json()
    print("Running GitHub checks as " + github_user["login"])
    travis_user = travis.get("/user").json()
    print("Running Travis checks as " + travis_user["login"])
    need_work = 0
    for repo in repos:
        if not validate_repo(repo):
            need_work += 1
            print()
    print("{} out of {} repos need work.".format(need_work, len(repos)))
