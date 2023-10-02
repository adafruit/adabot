# SPDX-FileCopyrightText: 2023 Tim Cocks
#
# SPDX-License-Identifier: MIT

"""
make a new release using the gh cli
"""
import subprocess

config = {"RELEASE_TITLE": ""}


def make_release(new_tag, logger):
    """
    Make the release
    """
    # pylint: disable=line-too-long

    while config["RELEASE_TITLE"] == "":
        config["RELEASE_TITLE"] = input("Enter a Release Title: ")

    result = subprocess.getoutput(
        f"gh release create {new_tag} -F release_notes.md -t '{new_tag} - {config['RELEASE_TITLE']}'"
    )

    if logger is not None:
        logger.info(result)
    else:
        print(result)
