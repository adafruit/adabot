# SPDX-FileCopyrightText: 2023 Tim Cocks
#
# SPDX-License-Identifier: MIT

"""
Check if a new release needs to be made, and if so, make it.
"""
import subprocess
import time
from compare_release_with_latest_commit import needs_new_release
from get_pypi_name import get_pypi_name
from create_release_notes import create_release_notes
from make_release import make_release
from get_release_info import get_release_info

result = subprocess.getoutput("git checkout main")

if needs_new_release():
    release_info = get_release_info()
    print(f"Making a new release with tag: {release_info['new_tag']}")
    create_release_notes(get_pypi_name())
    make_release()
else:
    print("No new commits since last release, skipping")

time.sleep(5)
