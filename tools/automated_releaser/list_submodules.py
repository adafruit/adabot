# SPDX-FileCopyrightText: 2023 Tim Cocks
#
# SPDX-License-Identifier: MIT

"""
Create txt files listing all current submodules of the bundle repo.
"""
import os

drivers = os.listdir("libraries/drivers/")
helpers = os.listdir("libraries/helpers/")

drivers.sort()
helpers.sort()

with open("drivers.txt", "w") as f:
    for i, submodule in enumerate(drivers):
        if i < len(drivers) - 1:
            f.write("{}\n".format(submodule))
        else:
            f.write("{}".format(submodule))

with open("helpers.txt", "w") as f:
    for i, submodule in enumerate(helpers):
        if i < len(helpers) - 1:
            f.write("{}\n".format(submodule))
        else:
            f.write("{}".format(submodule))
