# SPDX-FileCopyrightText: 2022 Alec Delaney, for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Checks for the latest releases in the Community bundle based
on the automated release.

* Author(s): Alec Delaney
"""

import os
from typing import Tuple
from typing_extensions import TypeAlias

import github as pygithub

GH_INTERFACE = pygithub.Github(os.environ.get("ADABOT_GITHUB_ACCESS_TOKEN"))

RepoResult: TypeAlias = Tuple[str, str]
"""(Submodule Name, Full Repo Name)"""


def get_community_bundle_updates() -> Tuple[RepoResult, RepoResult]:
    """"""
