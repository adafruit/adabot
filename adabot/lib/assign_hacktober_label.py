# SPDX-FileCopyrightText: 2019 Michael Schroeder
#
# SPDX-License-Identifier: MIT

"""An utility to automatically apply the 'hacktoberfest' label to open issues
marked as 'good first issue', during DigitalOcean's/GitHub's Hacktoberfest
event.
"""

import argparse
import datetime
import requests

from adabot import github_requests as gh_reqs
from adabot.lib import common_funcs

cli_args = argparse.ArgumentParser(description="Hacktoberfest Label Assigner")
cli_args.add_argument(
    "-r",
    "--remove-label",
    action="store_true",
    help="Option to remove Hacktoberfest labels, instead of adding them.",
    dest="remove_labels",
)
cli_args.add_argument(
    "--dry-run",
    action="store_true",
    help="Option to remove Hacktoberfest labels, instead of adding them.",
    dest="dry_run",
)


# Hacktoberfest Season
#  - lists are in [start, stop] format.
#  - tuples are in (month, day) format.
_ADD_SEASON = [(9, 29), (10, 30)]
_REMOVE_SEASON = [(11, 1), (11, 10)]


def is_hacktober_season():
    """Checks if the current day falls within either the add range (_ADD_SEASON)
    or the remove range (_REMOVE_SEASON). Returns boolean if within
    Hacktoberfest season, and which action to take.
    """
    today = datetime.date.today()
    add_range = [datetime.date(today.year, *month_day) for month_day in _ADD_SEASON]
    remove_range = [
        datetime.date(today.year, *month_day) for month_day in _REMOVE_SEASON
    ]
    if add_range[0] <= today <= add_range[1]:
        return True, "add"
    if remove_range[0] <= today <= remove_range[1]:
        return True, "remove"

    return False, None


def get_open_issues(repo):
    """Retrieve all open issues for given repo."""

    params = {
        "state": "open",
    }
    response = gh_reqs.get("/repos/" + repo["full_name"] + "/issues", params=params)
    if not response.ok:
        print(f"Failed to retrieve issues for '{repo['name']}'")
        return False

    issues = []
    while response.ok:
        issues.extend(
            [issue for issue in response.json() if "pull_request" not in issue]
        )

        if response.links.get("next"):
            response = requests.get(response.links["next"]["url"], timeout=30)
        else:
            break

    return issues


def ensure_hacktober_label_exists(repo, dry_run=False):
    """Checks if the 'Hacktoberfest' label exists on the repo.
    If not, creates the label.
    """
    response = gh_reqs.get(f"/repos/{repo['full_name']}/labels")
    if not response.ok:
        print(f"Failed to retrieve labels for '{repo['name']}'")
        return False

    repo_labels = [label["name"] for label in response.json()]

    hacktober_exists = {"Hacktoberfest", "hacktoberfest"} & set(repo_labels)
    if not hacktober_exists:
        params = {
            "name": "Hacktoberfest",
            "color": "f2b36f",
            "description": "DigitalOcean's Hacktoberfest",
        }
        if not dry_run:
            result = gh_reqs.post(f"/repos/{repo['full_name']}/labels", json=params)
            if not result.status_code == 201:
                print(f"Failed to create new Hacktoberfest label for: {repo['name']}")
                return False

    return True


def assign_hacktoberfest(repo, issues=None, remove_labels=False, dry_run=False):
    """Gathers open issues on a repo, and assigns the 'Hacktoberfest' label
    to each issue if its not already assigned.
    """
    labels_changed = 0

    if not issues:
        issues = get_open_issues(repo)

    for issue in issues:
        update_issue = False
        label_names = [label["name"] for label in issue["labels"]]
        has_good_first = "good first issue" in label_names
        has_hacktober = {"Hacktoberfest", "hacktoberfest"} & set(label_names)

        if remove_labels:
            if has_hacktober:
                label_names = [
                    label for label in label_names if label not in has_hacktober
                ]
                update_issue = True
        else:
            if has_good_first and not has_hacktober:
                label_exists = ensure_hacktober_label_exists(repo, dry_run)
                if not label_exists:
                    continue
                update_issue = True

        if update_issue:
            label_names.append("Hacktoberfest")
            params = {"labels": label_names}
            if not dry_run:
                result = gh_reqs.patch(
                    f"/repos/{repo['full_name']}/issues/{str(issue['number'])}",
                    json=params,
                )

                if result.ok:
                    labels_changed += 1
                else:
                    # sadly, GitHub will only silently ignore labels that are
                    # not added and return a 200. so this will most likely only
                    # trigger on endpoint/connection failures.
                    print(f"Failed to add Hacktoberfest label to: {issue['url']}")
            else:
                labels_changed += 1

    return labels_changed


def process_hacktoberfest(repo, issues=None, remove_labels=False, dry_run=False):
    """Run hacktoberfest functions and return the result."""
    result = assign_hacktoberfest(repo, issues, remove_labels, dry_run)
    return result


if __name__ == "__main__":
    LABELS_ASSIGNED = 0
    args = cli_args.parse_args()

    if not args.remove_labels:
        print("Checking for open issues to assign the Hacktoberfest label to...")
    else:
        print("Checking for open issues to remove the Hacktoberfest label from...")

    repos = common_funcs.list_repos()
    for repository in repos:
        LABELS_ASSIGNED += process_hacktoberfest(
            repository, remove_labels=args.remove_labels, dry_run=args.dry_run
        )

    if not args.remove_labels:
        print(f"Added the Hacktoberfest label to {LABELS_ASSIGNED} issues.")
    else:
        print(f"Removed the Hacktoberfest label from {LABELS_ASSIGNED} issues.")
