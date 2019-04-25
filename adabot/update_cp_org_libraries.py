# The MIT License (MIT)
#
# Copyright (c) 2019 Michael Schroeder
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

import argparse
import datetime
import inspect
import json
import os
import sh
from sh.contrib import git
import sys

from adabot.lib import common_funcs
from adabot.lib import circuitpython_library_validators as cpy_vals
from adabot import github_requests as github

# Setup ArgumentParser
cmd_line_parser = argparse.ArgumentParser(description="Adabot utility for updating circuitpython.org libraries info.",
                                          prog="Adabot circuitpython.org/libraries Updater")
cmd_line_parser.add_argument("-o", "--output_file", help="Output JSON file to the filename provided.",
                             metavar="<OUTPUT FILENAME>", dest="output_file")

def is_new_or_updated(repo):
    """ Check the repo for new release(s) within the last week. Then determine
        if all releases are within the last week to decide if this is a newly
        released library, or an updated library.
    """

    today_minus_seven = datetime.datetime.today() - datetime.timedelta(days=7)

    # first, check the latest release to see if within the last 7 days
    result = github.get("/repos/adafruit/" + repo["name"] + "/releases/latest")
    if not result.ok:
        return
    release_info = result.json()
    if "published_at" not in release_info:
        return
    else:
        release_date = datetime.datetime.strptime(release_info["published_at"], "%Y-%m-%dT%H:%M:%SZ")
        if release_date < today_minus_seven:
            return

    # we have a release within the last 7 days. now check if its a newly released library
    # within the last week, or if its just an update
    result = github.get("/repos/adafruit/" + repo["name"] + "/releases")
    if not result.ok:
        return

    new_releases = 0
    releases = result.json()
    for release in releases:
        release_date = datetime.datetime.strptime(release["published_at"], "%Y-%m-%dT%H:%M:%SZ")
        if not release_date < today_minus_seven:
            new_releases += 1

    if new_releases == len(releases):
        return "new"
    else:
        return "updated"

def get_open_issues_and_prs(repo):
    """ Retreive all of the open issues (minus pull requests) for the repo.
    """
    open_issues = []
    open_pull_requests = []
    params = {"state":"open"}
    result = github.get("/repos/adafruit/" + repo["name"] + "/issues", params=params)
    if not result.ok:
        return [], []

    issues = result.json()
    for issue in issues:
        if "pull_request" not in issue: # ignore pull requests
            open_issues.append({issue["html_url"]: issue["title"]})
        else:
            open_pull_requests.append({issue["html_url"]: issue["title"]})

    return open_issues, open_pull_requests

def get_contributors(repo):
    contributors = []
    reviewers = []
    merged_pr_count = 0
    params = {"state":"closed", "sort":"updated", "direction":"desc"}
    result = github.get("/repos/adafruit/" + repo["name"] + "/pulls", params=params)
    if result.ok:
        today_minus_seven = datetime.datetime.today() - datetime.timedelta(days=7)
        prs = result.json()
        for pr in prs:
            merged_at = datetime.datetime.min
            if "merged_at" in pr:
                if pr["merged_at"] is None:
                    continue
                merged_at = datetime.datetime.strptime(pr["merged_at"], "%Y-%m-%dT%H:%M:%SZ")
            else:
                continue
            if merged_at < today_minus_seven:
                continue
            contributors.append(pr["user"]["login"])
            merged_pr_count += 1

            # get reviewers (merged_by, and any others)
            single_pr = github.get(pr["url"])
            if not single_pr.ok:
                continue
            pr_info = single_pr.json()
            reviewers.append(pr_info["merged_by"]["login"])
            pr_reviews = github.get(str(pr_info["url"]) + "/reviews")
            if not pr_reviews.ok:
                continue
            for review in pr_reviews.json():
                if review["state"].lower() == "approved":
                    reviewers.append(review["user"]["login"])

    return contributors, reviewers, merged_pr_count

def update_json_file(working_directory, cp_org_dir, output_filename, json_string):
    """ Clone the circuitpython-org repo, update libraries.json, and push the updates
        in a commit.
    """
    if "TRAIVS" in os.environ:
        if not os.path.isdir(cp_org_dir):
            os.makedirs(cp_org_dir, exist_ok=True)
            git_url = "https://" + os.environ["ADABOT_GITHUB_ACCESS_TOKEN"] + "@github.com/adafruit/circuitpython-org.git"
            git.clone("-o", "adafruit", git_url, cp_org_dir)
        os.chdir(cp_org_dir)
        git.pull()
        git.submodule("update", "--init", "--recursive")

        with open(output_filename, "w") as json_file:
            json.dump(json_string, json_file, indent=2)

        commit_day = date.date.strftime(datetime.datetime.today(), "%Y-%m-%d")
        commit_msg = "adabot: auto-update of libraries.json ({})".format(commit_day)
        git.commit("-a", "-m", commit_msg)
        git_push = git.push("adafruit", "master")
        print(git_push)

if __name__ == "__main__":
    cmd_line_args = cmd_line_parser.parse_args()

    print("Running circuitpython.org/libraries updater...")

    run_time = datetime.datetime.now()
    # Travis CI weekly cron jobs do not allow or guarantee that they will be run
    # on a specific day of the week. So, we set the cron to run daily, and then
    # check for the day we want this to run.
    if "TRAVIS" in os.environ:
        should_run = int(os.environ["CP_ORG_UPDATER_RUN_DAY"])
        if datetime.datetime.weekday(run_time) != should_run:
            should_run_date = datetime.date.today() - datetime.timedelta(days=(6 - should_run))
            msg = [
                "Aborting...",
                " - Today is not {}.".format(should_run_date.strftime("%A")),
                " - To run the updater on a different day, change the",
                "   'CP_ORG_UPDATER_RUN_DAY' environment variable in Travis.",
                " - Day is a number between 0 & 6, with 0 being Monday."
            ]
            print("\n".join(msg))
            sys.exit()

    working_directory = os.path.abspath(os.getcwd())
    cp_org_dir = os.path.join(working_directory, ".cp_org")

    startup_message = ["Run Date: {}".format(run_time.strftime("%d %B %Y, %I:%M%p"))]

    output_filename = os.path.join(cp_org_dir, "_data/libraries.json")
    local_file_output = False
    if cmd_line_args.output_file:
        output_filename = os.path.abspath(cmd_line_args.output_file)
        local_file_output = True
    startup_message.append(" - Output will be saved to: {}".format(output_filename))

    print("\n".join(startup_message))

    repos = common_funcs.list_repos()

    new_libs = {}
    updated_libs = {}
    open_issues_by_repo = {}
    open_prs_by_repo = {}
    contributors = []
    reviewers = []
    merged_pr_count_total = 0
    repos_by_error = {}

    default_validators = [vals[1] for vals in inspect.getmembers(cpy_vals.library_validator) if vals[0].startswith("validate")]
    bundle_submodules = common_funcs.get_bundle_submodules()
    validator = cpy_vals.library_validator(default_validators, bundle_submodules, 0.0)

    for repo in repos:
        if repo["name"] in cpy_vals.BUNDLE_IGNORE_LIST or repo["name"] == "circuitpython":
            continue
        repo_name = repo["name"]

        # get a list of new & updated libraries for the last week
        check_releases = is_new_or_updated(repo)
        if check_releases == "new":
            new_libs[repo_name] = repo["html_url"]
        elif check_releases == "updated":
            updated_libs[repo_name] = repo["html_url"]

        # get a list of open issues and pull requests
        check_issues, check_prs = get_open_issues_and_prs(repo)
        if check_issues:
            open_issues_by_repo[repo_name] = check_issues
        if check_prs:
            open_prs_by_repo[repo_name] = check_prs

        # get the contributors and reviewers for the last week
        get_contribs, get_revs, get_merge_count = get_contributors(repo)
        if get_contribs:
            contributors.extend(get_contribs)
        if get_revs:
            reviewers.extend(get_revs)
        merged_pr_count_total += get_merge_count

        # run repo validators to check for infrastructure errors
        errors = validator.run_repo_validation(repo)
        for error in errors:
            if not isinstance(error, tuple):
                # check for an error occurring in the valiator module
                if error == cpy_vals.ERROR_OUTPUT_HANDLER:
                    #print(errors, "repo output handler error:", validator.output_file_data)
                    print(", ".join(validator.output_file_data))
                    validator.output_file_data.clear()
                if error not in repos_by_error:
                    repos_by_error[error] = []
                repos_by_error[error].append(repo["html_url"])
            else:
                if error[0] not in repos_by_error:
                    repos_by_error[error[0]] = []
                repos_by_error[error[0]].append("{0} ({1} days)".format(repo["html_url"], error[1]))

    # sort all of the items alphabetically
    sorted_new_list = {}
    for new in sorted(new_libs, key=str.lower):
        sorted_new_list[new] = new_libs[new]

    sorted_updated_list = {}
    for updated in sorted(updated_libs, key=str.lower):
        sorted_updated_list[updated] = updated_libs[updated]

    sorted_issues_list = {}
    for issue in sorted(open_issues_by_repo, key=str.lower):
        sorted_issues_list[issue] = open_issues_by_repo[issue]

    sorted_prs_list = {}
    for pr in sorted(open_prs_by_repo, key=str.lower):
        sorted_prs_list[pr] = open_prs_by_repo[pr]

    sorted_repos_by_error = {}
    for error in sorted(repos_by_error, key=str.lower):
        sorted_repos_by_error[error] = repos_by_error[error]

    # assemble the JSON data
    build_json = {
        "updated_at": run_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "contributors": [contrib for contrib in set(contributors)],
        "reviewers": [rev for rev in set(reviewers)],
        "merged_pr_count": str(merged_pr_count_total),
        "library_updates": {"new": sorted_new_list, "updated": sorted_updated_list},
        "open_issues": sorted_issues_list,
        "pull_requests": sorted_prs_list,
        "repo_infrastructure_errors": sorted_repos_by_error,
    }
    json_obj = json.dumps(build_json, indent=2)

    if "TRAVIS" in os.environ:
        update_json_file(working_directory, cp_org_dir, output_filename, build_json)
    else:
        if local_file_output:
            with open(output_filename, "w") as json_file:
                json.dump(build_json, json_file, indent=2)
    print(json.dumps(build_json, indent=2))
