# SPDX-FileCopyrightText: 2023 Tim Cocks
#
# SPDX-License-Identifier: MIT

"""
Get infomation about the latest release.
- Current tag name
- New tag name assuming +1 to minor version
- timestamp for when the release was created
"""
import subprocess


def get_release_info():
    """
    return a dictionary of info about the latest release
    """
    result = subprocess.getoutput("gh release list -L 1 | awk 2")
    createdAt = result.split("\t")[-1]
    tag = result.split("\t")[-2]

    tag_parts = tag.split(".")

    tag_parts[-1] = str(int(tag_parts[-1]) + 1)

    new_tag = ".".join(tag_parts)

    return {"current_tag": tag, "new_tag": new_tag, "created_at": createdAt}
