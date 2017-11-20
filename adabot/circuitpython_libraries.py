# The MIT License (MIT)
#
# Copyright (c) 2017 Scott Shawcroft for Adafruit Industries
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

from adabot import requests
import sys

def list_repos():
    result = requests.get("https://api.github.com/search/repositories?q=Adafruit_CircuitPython+in%3Aname")
    return result.json()["items"]

def validate_teams(repo):
    if repo["owner"]["login"] != "adafruit":
        return True
    result = requests.get(repo["teams_url"]+"?v=1")
    ok = False
    for team in result.json():
        ok = ok or team["name"] == "CircuitPythonLibrarians"
    if not ok:
        print(repo["full_name"], "missing CircuitPythonLibrarians team.")
    return ok

validators = [validate_teams]

def validate_repo(repo):
    for validator in validators:
        validator(repo)

if __name__ == "__main__":
    for repo in list_repos():
        validate_repo(repo)
