# The MIT License (MIT)
#
# Copyright (c) 2017 Scott Shawcroft for Adafruit Industries
#               2019 Michael Schroeder
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
import inspect

import requests

from adabot import github_requests as github
from adabot import travis_requests as travis
from adabot import pypi_requests as pypi
from adabot.lib import circuitpython_library_validators as cirpy_lib_vals
from adabot.lib import common_funcs
from adabot.lib import assign_hacktober_label as hacktober
from adabot.lib import blinka_funcs
from adabot import circuitpython_library_download_stats as dl_stats

# Setup ArgumentParser
cmd_line_parser = argparse.ArgumentParser(
    description="Adabot utility for CircuitPython Libraries.",
    prog="Adabot CircuitPython Libraries Utility"
)
cmd_line_parser.add_argument(
    "-o", "--output_file",
    help="Output log to the filename provided.",
    metavar="<OUTPUT FILENAME>",
    dest="output_file"
)
cmd_line_parser.add_argument(
    "-p", "--print",
    help="Set the level of verbosity printed to the command prompt."
    " Zero is off; One is on (default).",
    type=int,
    default=1,
    dest="verbose",
    choices=[0,1]
)
cmd_line_parser.add_argument(
    "-e", "--error_depth",
    help="Set the threshold for outputting an error list. Default is 5.",
    dest="error_depth",
    type=int,
    default=5,
    metavar="n"
)
cmd_line_parser.add_argument(
    "-t", "--travis-github-token",
    help="Prompt for the GitHub user's password in order to make a GitHub token to use on Travis.",
    dest="gh_token",
    action="store_true"
)
cmd_line_parser.add_argument(
    "-v", "--validator",
    help="Run validators with 'all', or only the validator(s) supplied in a string.",
    dest="validator",
    metavar='all OR "validator1, validator2, ..."'
)

# Define global state shared by the functions above:
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

# Functions to run on repositories to validate their state.  By convention these
# return a list of string errors for the specified repository (a dictionary
# of Github API repository object state).
default_validators = [
    vals for vals in inspect.getmembers(cirpy_lib_vals.library_validator)
    if vals[0].startswith("validate")
]

pr_sort_re = re.compile("(?<=\(Open\s)(.+)(?=\sdays)")

def run_library_checks(validators, bundle_submodules, latest_pylint, kw_args):
    """runs the various library checking functions"""
    pylint_info = pypi.get("/pypi/pylint/json")
    if pylint_info and pylint_info.ok:
        latest_pylint = pylint_info.json()["info"]["version"]
    output_handler("Latest pylint is: {}".format(latest_pylint))

    repos = common_funcs.list_repos(include_repos=('Adafruit_Blinka',))
    output_handler("Found {} repos to check.".format(len(repos)))
    bundle_submodules = common_funcs.get_bundle_submodules()
    output_handler("Found {} submodules in the bundle.".format(len(bundle_submodules)))
    github_user = common_funcs.whois_github_user()
    output_handler("Running GitHub checks as " + github_user)
    need_work = 0

    lib_insights = common_funcs.InsightData()
    blinka_insights = common_funcs.InsightData()
    core_insights = common_funcs.InsightData()
    core_insights["milestones"] = dict()

    repo_needs_work = []
    since = datetime.datetime.now() - datetime.timedelta(days=7)
    repos_by_error = {}
    new_libs = {}
    updated_libs = {}

    validator = cirpy_lib_vals.library_validator(validators,
                                                 bundle_submodules,
                                                 latest_pylint, **kw_args)
    for repo in repos:
        if len(validators) != 0:
            errors = validator.run_repo_validation(repo)
            if errors:
                need_work += 1
                repo_needs_work.append(repo)
                # print(repo["full_name"])
                # print("\n".join(errors))
                # print()
            for error in errors:
                if not isinstance(error, tuple):
                    # check for an error occurring in the valiator module
                    if error == cirpy_lib_vals.ERROR_OUTPUT_HANDLER:
                        #print(errors, "repo output handler error:", validator.output_file_data)
                        output_handler(", ".join(validator.output_file_data))
                        validator.output_file_data.clear()
                    if error not in repos_by_error:
                        repos_by_error[error] = []
                    repos_by_error[error].append(repo["html_url"])
                else:
                    if error[0] not in repos_by_error:
                        repos_by_error[error[0]] = []
                    repos_by_error[error[0]].append(
                        "{0} ({1} days)".format(repo["html_url"], error[1])
                    )
        insights = lib_insights
        if repo["owner"]["login"] == "adafruit":
            if repo["name"] == "Adafruit_Blinka":
                insights = blinka_insights
            elif repo["name"] == "circuitpython":
                insights = core_insights
        errors = validator.gather_insights(repo, insights, since)
        if errors:
            print("insights error")
            for error in errors:
                if error == cirpy_lib_vals.ERROR_OUTPUT_HANDLER:
                    output_handler(", ".join(validator.output_file_data))
                    validator.output_file_data.clear()

        # get a list of new & updated libraries for the last week
        if repo["name"] != "Adafruit_CircuitPython_Bundle":
            check_releases = common_funcs.is_new_or_updated(repo)
            if check_releases == "new":
                new_libs[repo["name"]] = repo["html_url"]
            elif check_releases == "updated":
                updated_libs[repo["name"]] = repo["html_url"]

    output_handler()
    output_handler("State of CircuitPython + Libraries")

    output_handler("Overall")
    print_pr_overview(lib_insights, core_insights)
    print_issue_overview(lib_insights, core_insights)

    output_handler()
    output_handler("Core")
    print_pr_overview(core_insights)
    output_handler("* {} open pull requests".format(len(core_insights["open_prs"])))
    sorted_prs = sorted(core_insights["open_prs"],
                        key=lambda days: int(pr_sort_re.search(days).group(1)),
                        reverse=True)
    for pr in sorted_prs:
        output_handler("  * {}".format(pr))
    print_issue_overview(core_insights)
    output_handler("* {} open issues".format(len(core_insights["open_issues"])))
    output_handler("  * https://github.com/adafruit/circuitpython/issues")
    output_handler("* {} active milestones".format(len(core_insights["milestones"])))
    ms_count = 0
    for milestone in sorted(core_insights["milestones"].keys()):
        ms_count += core_insights["milestones"][milestone]
        output_handler("  * {0}: {1} open issues".format(milestone,
                                                         core_insights["milestones"][milestone]))
    output_handler("  * {} issues not assigned a milestone".format(len(core_insights["open_issues"]) - ms_count))
    output_handler()
    print_circuitpython_download_stats()

    output_handler()
    output_handler("Libraries")
    print_pr_overview(lib_insights)
    output_handler("* {} open pull requests".format(len(lib_insights["open_prs"])))
    sorted_prs = sorted(lib_insights["open_prs"],
                        key=lambda days: int(pr_sort_re.search(days).group(1)),
                        reverse=True)
    for pr in sorted_prs:
        output_handler("  * {}".format(pr))
    print_issue_overview(lib_insights)
    output_handler("* {} open issues".format(len(lib_insights["open_issues"])))
    output_handler("  * https://circuitpython.org/contributing")
    output_handler("Library updates in the last seven days:")
    if len(new_libs) != 0:
        output_handler("**New Libraries**")
        for new in new_libs:
            output_handler(" * [{}]({})".format(new, new_libs[new]))
    if len(updated_libs) != 0:
        output_handler("**Updated Libraries**")
        for updated in updated_libs:
            output_handler(" * [{}]({})".format(updated, updated_libs[updated]))

    if len(validators) != 0:
        lib_repos = []
        for repo in repos:
            if (repo["owner"]["login"] == "adafruit" and
                repo["name"].startswith("Adafruit_CircuitPython")):
                    lib_repos.append(repo)

        output_handler("{} out of {} repos need work.".format(need_work,
                                                              len(lib_repos)))

        list_repos_for_errors = [cirpy_lib_vals.ERROR_NOT_IN_BUNDLE]
        output_handler()
        for error in sorted(repos_by_error):
            if not repos_by_error[error]:
                continue
            output_handler()
            error_count = len(repos_by_error[error])
            output_handler("{} - {}".format(error, error_count))
            if error_count <= error_depth or error in list_repos_for_errors:
                output_handler("\n".join(["  * " + x for x in repos_by_error[error]]))

    output_handler()
    output_handler("Blinka")
    print_pr_overview(blinka_insights)
    output_handler("* {} open pull requests".format(len(blinka_insights["open_prs"])))
    sorted_prs = sorted(blinka_insights["open_prs"],
                        key=lambda days: int(pr_sort_re.search(days).group(1)),
                        reverse=True)
    for pr in sorted_prs:
        output_handler("  * {}".format(pr))
    print_issue_overview(blinka_insights)
    output_handler("* {} open issues".format(len(blinka_insights["open_issues"])))
    output_handler("  * https://github.com/adafruit/Adafruit_Blinka/issues")
    blinka_dl, _ = dl_stats.pypistats_get('adafruit-blinka')
    output_handler("* PyPI Downloads in the last week: {}".format(blinka_dl))
    output_handler(
        "Number of supported boards: {}".format(blinka_funcs.board_count())
    )

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
    stable_tag = None
    prerelease_tag = None

    by_board = {}
    by_language = {}
    by_both = {}
    total = {}

    asset_re = re.compile(
        r"""
            circuitpython\-   # end of the prefix
            (?P<board>.+)\-   # board name
            (?P<lang>.+)\-    # language
            (\d\.\d\.\d.*)    # version
            \.(?=uf2|bin|hex) # file extension
        """,
        re.I | re.X
    )

    for release in releases:
        if not found_unstable and not release["draft"] and release["prerelease"]:
            found_unstable = True
            prerelease_tag = release["tag_name"]
        elif not found_stable and not release["draft"] and not release["prerelease"]:
            found_stable = True
            stable_tag = release["tag_name"]
        else:
            continue

        for asset in release["assets"]:
            if not asset["name"].startswith("adafruit-circuitpython"):
                continue
            count = asset["download_count"]
            info_re = asset_re.search(asset["name"])
            if not info_re:
                print("Skipping stats for '{}'".format(asset["name"]))
                continue
            board = info_re.group("board")
            language = info_re.group("lang")
            if language not in by_language:
                by_language[language] = {release["tag_name"]: 0}
            if release["tag_name"] not in by_language[language]:
                by_language[language][release["tag_name"]] = 0
            by_language[language][release["tag_name"]] += count
            if board not in by_board:
                by_board[board] = {release["tag_name"]: 0}
                by_both[board] = {}
            if release["tag_name"] not in by_board[board]:
                by_board[board][release["tag_name"]] = 0
            by_board[board][release["tag_name"]] += count
            by_both[board][language] = count

            if release["tag_name"] not in total:
                total[release["tag_name"]] = 0
            total[release["tag_name"]] += count

    output_handler("Number of supported boards: {}".format(len(by_board)))
    output_handler()
    output_handler("Download stats by board:")
    output_handler()
    by_board_list = [["Board", "{}".format(stable_tag.strip(" ")), "{}".format(prerelease_tag.strip(" "))],]
    for board in sorted(by_board.items()):
        by_board_list.append([str(board[0]),
                              (str(board[1][stable_tag]) if stable_tag in board[1] else "-"),
                              (str(board[1][prerelease_tag]) if prerelease_tag in board[1] else "-")])

    long_col = [(max([len(str(row[i])) for row in by_board_list]) + 3)
                for i in range(len(by_board_list[0]))]
    #row_format = "".join(["{:<" + str(this_col) + "}" for this_col in long_col])
    row_format = "".join(["| {:<" + str(long_col[0]) + "}",
                          "|{:^" + str(long_col[1]) + "}",
                          "|{:^" + str(long_col[2]) + "}|"])

    by_board_list.insert(1,
                         ["{}".format("-"*(long_col[0])),
                          "{}".format("-"*(long_col[1])),
                          "{}".format("-"*(long_col[2]))])

    by_board_list.extend((["{}".format("-"*(long_col[0])),
                          "{}".format("-"*(long_col[1])),
                          "{}".format("-"*(long_col[2]))],
                         ["{0}{1}".format(" "*(long_col[0] - 6), "Total"),
                          "{}".format(total[stable_tag]),
                          "{}".format(total[prerelease_tag])],
                         ["{}".format("-"*(long_col[0])),
                          "{}".format("-"*(long_col[1])),
                          "{}".format("-"*(long_col[2]))]))

    for row in by_board_list:
        output_handler(row_format.format(*row))
    output_handler()

    output_handler("Download stats by language:")
    output_handler()
    by_lang_list = [["Board", "{}".format(stable_tag.strip(" ")), "{}".format(prerelease_tag.strip(" "))],]
    for board in sorted(by_language.items()):
        by_lang_list.append([str(board[0]),
                              (str(board[1][stable_tag]) if stable_tag in board[1] else "-"),
                              (str(board[1][prerelease_tag]) if prerelease_tag in board[1] else "-")])

    long_col = [(max([len(str(row[i])) for row in by_lang_list]) + 3)
                for i in range(len(by_lang_list[0]))]
    #row_format = "".join(["{:<" + str(this_col) + "}" for this_col in long_col])
    row_format = "".join(["| {:<" + str(long_col[0]) + "}",
                          "|{:^" + str(long_col[1]) + "}",
                          "|{:^" + str(long_col[2]) + "}|"])

    by_lang_list.insert(1,
                         ["{}".format("-"*(long_col[0])),
                          "{}".format("-"*(long_col[1])),
                          "{}".format("-"*(long_col[2]))])

    by_lang_list.extend((["{}".format("-"*(long_col[0])),
                          "{}".format("-"*(long_col[1])),
                          "{}".format("-"*(long_col[2]))],
                         ["{0}{1}".format(" "*(long_col[0] - 6), "Total"),
                          "{}".format(total[stable_tag]),
                          "{}".format(total[prerelease_tag])],
                         ["{}".format("-"*(long_col[0])),
                          "{}".format("-"*(long_col[1])),
                          "{}".format("-"*(long_col[2]))]))

    for row in by_lang_list:
        output_handler(row_format.format(*row))
    #for language in by_language:
    #    output_handler("* {} - {}".format(language, by_language[language]))
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

    # print Hacktoberfest labels changes if its Hacktober
    in_season, season_action = hacktober.is_hacktober_season()
    if in_season:
        hacktober_changes = ""
        if season_action == "add":
            hacktober_changes = "* Assigned Hacktoberfest label to {} issues.".format(
                sum([x["hacktober_assigned"] for x in insights])
            )
        elif season_action == "remove":
            hacktober_changes += "* Removed Hacktoberfest label from {} issues.".format(
                sum([x["hacktober_removed"] for x in insights])
            )
        output_handler(hacktober_changes)

if __name__ == "__main__":
    validator_kwarg_list = {}
    startup_message = [
        "Running CircuitPython Library checks...",
        "Report Date: {}".format(datetime.datetime.now().strftime("%d %B %Y, %I:%M%p"))
    ]
    cmd_line_args = cmd_line_parser.parse_args()

    verbosity = cmd_line_args.verbose

    if cmd_line_args.output_file:
        output_filename = cmd_line_args.output_file
        startup_message.append(" - Report output will be saved to: {}".format(output_filename))

    validators = []
    validator_names = []
    if cmd_line_args.validator:
        error_depth = cmd_line_args.error_depth
        startup_message.append(" - Depth for listing libraries with errors: {}".format(error_depth))

        github_token = cmd_line_args.gh_token
        validator_kwarg_list["github_token"] = github_token
        startup_message.append(" - Prompts for the GitHub Token are {}.".format(("enabled" if github_token else "disabled")))

        if cmd_line_args.validator != "all":
            validators = []
            for func in cmd_line_args.validator.split(","):
                func_name = func.strip()
                try:
                    if not func_name.startswith("validate"):
                        raise KeyError
                        #print('{}'.format(func_name))
                    if "contents" not in func_name:
                        validators.append(
                            [val[1] for val in default_validators if func_name in val[0]][0]
                        )
                    else:
                        validators.insert(
                            0,
                            [val[1] for val in default_validators if func_name in val[0]][0]
                        )
                    validator_names.append(func_name)
                except KeyError:
                    #print(default_validators)
                    output_handler("Error: '{0}' is not an available validator.\n" \
                                   "Available validators are: {1}".format(func.strip(),
                                   ", ".join([val[0] for val in default_validators])))
                    sys.exit()
        else:
            validators = [val_funcs[1] for val_funcs in default_validators]
            validator_names = [val_names[0] for val_names in default_validators]

        startup_message.append(" - These validators will run: {}".format(", ".join(validator_names)))

        if "validate_contents" not in validator_names:
            validator_kwarg_list["validate_contents_quiet"] = True
            validators.insert(
                0, [val[1] for val in default_validators if "validate_contents" in val[0]][0]
            )

    try:
        for message in startup_message:
            output_handler(message)
        output_handler()
        #print(validators)
        run_library_checks(validators, bundle_submodules, latest_pylint,
                           validator_kwarg_list)
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
