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


def bump_major(tag_symver):
    """
    Returns a string with a new tag created by incrementing
    the major version of the given semantic version tag.
    """
    tag_parts = tag_symver.split(".")
    tag_parts[0] = str(int(tag_parts[0]) + 1)
    tag_parts[1] = "0"
    tag_parts[2] = "0"
    return ".".join(tag_parts)


def bump_minor(tag_symver):
    """
    Returns a string with a new tag created by incrementing
    the minor version of the given semantic version tag.
    """
    tag_parts = tag_symver.split(".")
    tag_parts[1] = str(int(tag_parts[1]) + 1)
    tag_parts[2] = "0"
    return ".".join(tag_parts)


def bump_patch(tag_symver):
    """
    Returns a string with a new tag created by incrementing
    the patch version of the given semantic version tag.
    """
    tag_parts = tag_symver.split(".")
    tag_parts[-1] = str(int(tag_parts[-1]) + 1)
    return ".".join(tag_parts)


def get_release_info():
    """
    return a dictionary of info about the latest release
    """
    result = subprocess.getoutput("gh release list -L 1 | awk 2")
    createdAt = result.split("\t")[-1]
    tag = result.split("\t")[-2]

    return {
        "current_tag": tag,
        "new_tag_patch": bump_patch(tag),
        "new_tag_minor": bump_minor(tag),
        "new_tag_major": bump_major(tag),
        "created_at": createdAt,
    }
