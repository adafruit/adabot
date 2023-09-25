# SPDX-FileCopyrightText: 2023 Tim Cocks
#
# SPDX-License-Identifier: MIT

"""
Copy the scripts needed for releasing into the current directory.
Assumes library bundle struction and files pasted into position as instructed in README.md.
"""
import os

os.system("cp -r ../../../release_maker_scripts/* ./")
