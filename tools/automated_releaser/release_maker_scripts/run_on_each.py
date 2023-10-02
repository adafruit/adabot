# SPDX-FileCopyrightText: 2023 Tim Cocks
#
# SPDX-License-Identifier: MIT

"""
Check if a new release needs to be made, and if so, make it.
"""
import subprocess
import logging
from compare_release_with_latest_commit import needs_new_release
from get_pypi_name import get_pypi_name
from create_release_notes import create_release_notes
from make_release import make_release
from get_release_info import get_release_info


VALID_CHOICES = ("1", "2", "3", "4", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("../../../automated_releaser.log"),
        logging.StreamHandler(),
    ],
)


def menu_prompt(release_info):
    """
    Prompt the user to ask which part of the symantic version should be
    incremented, or if the library release should be skipped.
    Returns the choice inputted by the user.
    """
    print("This library needs a new release. Please select a choice:")
    print(f"1. *default* Bump Patch, new tag would be: {release_info['new_tag_patch']}")
    print(f"2. Bump Minor, new tag would be: {release_info['new_tag_minor']}")
    print(f"3. Bump Major, new tag would be: {release_info['new_tag_major']}")
    print("4. Skip releasing this library and go to next in the list")
    return input("Choice, enter blank for default: ")


result = subprocess.getoutput("git checkout main")

result = subprocess.getoutput("pwd")
logging.info("Checking: %s", "/".join(result.split("/")[-3:]))

if needs_new_release(logging):
    release_info = get_release_info()
    choice = menu_prompt(release_info)
    while choice not in VALID_CHOICES:
        logging.info("Error: Invalid Selection '%s'", choice)
        choice = menu_prompt(release_info)

    if choice in ("1", ""):
        logging.info("Making a new release with tag: %s", release_info["new_tag_patch"])
        create_release_notes(get_pypi_name())
        make_release(release_info["new_tag_patch"], logging)
    elif choice == "2":
        logging.info("Making a new release with tag: %s", release_info["new_tag_minor"])
        create_release_notes(get_pypi_name())
        make_release(release_info["new_tag_minor"], logging)
    elif choice == "3":
        logging.info("Making a new release with tag: %s", release_info["new_tag_major"])
        create_release_notes(get_pypi_name())
        make_release(release_info["new_tag_major"], logging)
    elif choice == "4":
        logging.info("Skipping release.")

else:
    logging.info("No new commits since last release, skipping")
