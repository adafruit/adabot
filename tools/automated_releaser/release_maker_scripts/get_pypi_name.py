# SPDX-FileCopyrightText: 2023 Tim Cocks
#
# SPDX-License-Identifier: MIT

"""
get the shorthand pypi name from the pyproject.toml file.
"""
import toml


def get_pypi_name():
    """
    return the shorthand pypi project name
    """
    data = toml.load("pyproject.toml")

    return data["project"]["name"].replace("adafruit-circuitpython-", "")
