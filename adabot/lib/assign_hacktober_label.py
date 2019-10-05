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
import requests

from adabot import github_requests as github
from adabot.lib import common_funcs

cli_args = argparse.ArgumentParser(description="Hacktoberfest Label Assigner")
cli_args.add_argument("-r", "--remove-label", action="store_true",
                     help="Option to remove Hacktoberfest labels, instead of adding them.",
                     dest="remove_label")


def get_open_issues(repo):
    """ Retrieve all open issues for given repo.
    """

    params = {
        "state": "open",
    }
    response = github.get("/repos/" + repo["full_name"] + "/issues", params=params)
    if not response.ok:
        print("Failed to retrieve issues for '{}'".format(repo["name"]))
        return False

    issues = []
    while response.ok:
        issues.extend([issue for issue in response.json() if "pull_request" not in issue])

        try:
            links = response.headers["Link"]
        except KeyError:
            break
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

    return issues


def ensure_hacktober_label_exists(repo):
    """ Checks if the 'Hacktoberfest' label exists on the repo.
        If not, creates the label.
    """
    response = github.get("/repos/" + repo["full_name"] + "/labels")
    if not response.ok:
        print("Failed to retrieve labels for '{}'".format(repo["name"]))
        return False

    repo_labels = [label["name"] for label in response.json()]

    hacktober_exists = {"Hacktoberfest", "hacktoberfest"} & set(repo_labels)
    if not hacktober_exists:
        params = {
            "name": "Hacktoberfest",
            "color": "f2b36f",
            "description": "DigitalOcean's Hacktoberfest"
        }
        result = github.post("/repos/" + repo["full_name"] + "/labels", json=params)
        if not result.status_code == 201:
            print("Failed to create new Hacktoberfest label for: {}".format(repo["name"]))
            return False

    return True

def assign_hacktoberfest(repo, issues=None, remove_labels=False):
    """ Gathers open issues on a repo, and assigns the 'Hacktoberfest' label
        to each issue if its not already assigned.
    """
    labels_assigned = 0

    if not issues:
        issues = get_open_issues(repo)

    for issue in issues:
        label_names = [label["name"] for label in issue["labels"]]
        has_good_first = "good first issue" in label_names
        has_hacktober = {"Hacktoberfest", "hacktoberfest"} & set(label_names)

        if remove_labels:
            if has_hacktober:
                label_names = [
                    label for label in lable_names
                    if label not in has_hacktober
                ]
        else:
            if has_good_first and not has_hacktober:
                label_exists = ensure_hacktober_label_exists(repo)
                if not label_exists:
                    continue

        params = {
            "labels": label_names
        }
        result = github.patch("/repos/"
                              + repo["full_name"]
                              + "/issues/"
                              + str(issue["number"]),
                              json=params)

        if result.ok:
            labels_changed += 1
        else:
            # sadly, GitHub will only silently ignore labels that are
            # not added and return a 200. so this will most likely only
            # trigger on endpoint/connection failures.
            print("Failed to add Hacktoberfest label to: {}".format(issue["url"]))

    return labels_changed

def process_hacktoberfest(repo, remove_labels=False):
    result = assign_hacktoberfest(repo, remove_labels)
    return result


if __name__ == "__main__":
    labels_assigned = 0
    args = cli_args.parse_args()

    remove_labels = args.remove_label

    if not remove_labels:
        print("Checking for open issues to assign the Hacktoberfest label to...")
    else:
        print("Checking for open issues to remove the Hacktoberfest label from...")

    repos = common_funcs.list_repos()
    for repo in repos:
        labels_assigned += process_hacktoberfest(repo, remove_labels)

    if not remove_labels:
        print("Added the Hacktoberfest label to {} issues.".format(labels_assigned))
    else:
        print("Removed the Hacktoberfest label from {} issues.".format(labels_assigned))
