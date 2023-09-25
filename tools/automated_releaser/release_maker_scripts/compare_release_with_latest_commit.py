# SPDX-FileCopyrightText: 2023 Tim Cocks
#
# SPDX-License-Identifier: MIT

"""
compare the timestamp of the most recent commit
with the timestamp of the latest release.
"""
import subprocess
from datetime import datetime
from get_release_info import get_release_info

date_format = "%Y-%m-%dT%H:%M:%SZ"

other_date_format = "%a %b %d %H:%M:%S %Y"


def needs_new_release():
    """
    return true if there are commits newer than the latest release
    """
    last_commit_time = subprocess.getoutput(
        " TZ=UTC0 git log -1 --date=local --format='%cd'"
    )
    print(f"last commit: {last_commit_time}")

    last_commit_date_obj = datetime.strptime(last_commit_time, other_date_format)

    release_info = get_release_info()

    print(f"Latest release is: {release_info['current_tag']}")
    print(f"createdAt: {release_info['created_at']}")

    release_date_obj = datetime.strptime(release_info["created_at"], date_format)
    return release_date_obj < last_commit_date_obj


if __name__ == "__main__":
    if needs_new_release():
        print("There are new commits")
    else:
        print("Nope, nothing in the cannon.")
