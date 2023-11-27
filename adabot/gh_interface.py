import os

import github

GH_INTERFACE = github.Github(os.environ.get("ADABOT_GITHUB_ACCESS_TOKEN"), retry=github.GithubRetry())

