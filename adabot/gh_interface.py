# SPDX-FileCopyrightText: 2023 Jeff Epler
#
# SPDX-License-Identifier: MIT
"""Get a properly-configured Github() object"""
import os

import github

GH_TOKEN = os.environ.get("ADABOT_GITHUB_ACCESS_TOKEN")
GH_INTERFACE = github.Github(
    auth=github.Auth.Token(GH_TOKEN) if GH_TOKEN else None, retry=github.GithubRetry()
)
