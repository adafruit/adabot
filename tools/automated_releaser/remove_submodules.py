# SPDX-FileCopyrightText: 2023 Tim Cocks
#
# SPDX-License-Identifier: MIT

"""
Remove submodules for any libraries named in drivers.txt or helpers.txt files which are created
by list_submodules.py.

This can be used to run automated actions against a subset of the full bundle by removing
some submodules leaving only the subset desired to run on.

The removal does not / should not be commited to the bundle, it's only to be made locally during
this automation process and then discarded / submodules restored to how they are in the main branch.
"""
import os

with open("drivers.txt", "r") as f:
    drivers = f.read().split("\n")


with open("helpers.txt", "r") as f:
    helpers = f.read().split("\n")

print(drivers)
print(helpers)

for driver in drivers:
    os.system("git submodule deinit -f libraries/drivers/{}/".format(driver))

for helper in helpers:
    os.system("git submodule deinit -f libraries/helpers/{}/".format(helper))
