# SPDX-FileCopyrightText: 2022 Alec Delaney, for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Checks for the latest releases in the Community bundle based
on the automated release.

* Author(s): Alec Delaney
"""

import datetime
import logging
import os
import time
from typing import Tuple, Set
from typing_extensions import TypeAlias

import github as pygithub
import parse

GH_INTERFACE = pygithub.Github(os.environ.get("ADABOT_GITHUB_ACCESS_TOKEN"))

RepoResult: TypeAlias = Tuple[str, str]
"""(Submodule Name, Full Repo Name)"""


def get_community_bundle_updates() -> Tuple[Set[RepoResult], Set[RepoResult]]:
    """
    Get the updates to the Community Bundle.

    Returns new and updated libraries
    """
    while True:
        try:
            repository = GH_INTERFACE.get_repo(
                "adafruit/CircuitPython_Community_Bundle"
            )
            seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
            recent_releases = [
                release
                for release in repository.get_releases()
                if release.created_at > seven_days_ago
            ]
            new_libs = set()
            updated_libs = set()
            for recent_release in recent_releases:
                relevant_lines = [
                    line
                    for line in recent_release.body.split("\n")
                    if line.startswith("Updated libraries")
                    or line.startswith("New libraries:")
                ]
                for relevant_line in relevant_lines:
                    lib_components = [
                        x.strip(",") for x in relevant_line.split(" ")[2:]
                    ]
                    for lib in lib_components:
                        comps = parse.parse("[{name:S}]({link_comp:S})", lib)
                        link: str = parse.search(
                            "{link:S}/releases", comps["link_comp"]
                        )["link"]
                        full_name = parse.search(
                            "https://github.com/{full_name:S}", link
                        )["full_name"]
                    if relevant_line.startswith("Updated libraries"):
                        updated_libs.add((full_name, link))
                    else:
                        new_libs.add((full_name, link))
            return (new_libs, updated_libs)

        except pygithub.RateLimitExceededException:
            core_rate_limit_reset = GH_INTERFACE.get_rate_limit().core.reset
            sleep_time = core_rate_limit_reset - datetime.datetime.now()
            logging.warning("Rate Limit will reset at: %s", core_rate_limit_reset)
            time.sleep(sleep_time.seconds)
            continue


if __name__ == "__main__":
    results = get_community_bundle_updates()
    for new_lib in results[0]:
        print(f"New libraries: {new_lib[0]} { {new_lib[1]} }")
    for updated_lib in results[1]:
        print(f"New libraries: {updated_lib[0]} { {updated_lib[1]} }")
