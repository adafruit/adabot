# The MIT License (MIT)
#
# Copyright (c) 2022 Eva Herrada
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Tool for running specific CircuitPython library validators one at a time.

IMPORTANT: Must be run from the top-level adabot directory (one directory up
           from this one)

Type `python3 runner.py` to run this file, and select the validator you want
to run
"""

import datetime
import inspect
import json

from adabot import pypi_requests as pypi
from adabot.lib import circuitpython_library_validators as cpy_vals
from adabot.lib import common_funcs
from adabot.lib.common_funcs import list_repos

default_validators = [
    vals[1]
    for vals in inspect.getmembers(cpy_vals.LibraryValidator)
    if vals[0].startswith("validate")
]

bundle_submodules = common_funcs.get_bundle_submodules()

LATEST_PYLINT = ""
pylint_info = pypi.get("/pypi/pylint/json")
if pylint_info and pylint_info.ok:
    LATEST_PYLINT = pylint_info.json()["info"]["version"]

validator = cpy_vals.LibraryValidator(
    default_validators,
    bundle_submodules,
    LATEST_PYLINT,
)

valids = {}
for count, val in enumerate(default_validators):
    t = str(val).split(" at", maxsplit=1)[0].split("Validator.", maxsplit=1)[1]
    valids[count] = t
    print(f"{count}:", t)

select = valids[
    int(input(f"Select a function to run [0-{len(default_validators)-1}]: "))
]
print(select)
selected = getattr(validator, select)
print(selected)

try:
    with open("repos.json", "r") as f:
        DATE = f.readline().rstrip()
except FileNotFoundError:
    DATE = ""

print(f"Last run: {DATE}")
if DATE != str(datetime.date.today()):
    with open("repos.json", "w") as f:
        print("Fetching Repos List")
        all_repos = list_repos()
        print("Got Repos List")
        f.write(str(datetime.date.today()) + "\n")
        f.write(json.dumps(all_repos))

with open("repos.json", "r") as f:
    all_repos = json.loads(f.read().split("\n")[1])

results = {}

for repo in all_repos:
    val = selected(repo)
    print(repo["name"])
    print(val)
    if len(val):
        if isinstance(val[0], tuple):
            if val[0][0] not in results:
                results[val[0][0]] = []
            results[val[0][0]].append(repo["name"])
        else:
            for i in val:
                if i not in results:
                    results[i] = []
                results[i].append(repo["name"])


print(results)
with open("adabot_run.txt", "w") as f:
    for k, v in results.items():
        f.write(k + "\n")
        for i in v:
            f.write(i + "\n")
        f.write("\n")
