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

docs_status.py
==============

Functionality for checking the ReadTheDocs build status for libraries
in the Adafruit CircuitPython Bundle

* Author(s): Alec Delaney

"""

from typing import Any, Optional
import parse
import requests
from github.Repository import Repository
from github.ContentFile import ContentFile
from tools.iterate_libraries import iter_remote_bundle_with_func, RemoteLibFunc_IterResult


def check_docs_status(lib_repo: Repository, rtd_token: str) -> Optional[bool]:
    """Checks a library for  the latest documentation build status with the
    requested information

    .. note::

        The ReadTheDocs token must have sufficient privileges for accessing
        the API; therefore, only a maintainer can use this functionality.

    :param str gh_token: The Github token to be used for with the Github
        API
    :param str rtd_token: A ReadTheDocs API token with sufficient privileges
    :return: Whether the documentation built successfully; returns None if it
        could not be determined
    :rtype: bool|None
    """

    # Get the README file contents
    content_file: ContentFile = lib_repo.get_contents("README.rst")
    readme_text = content_file.decoded_content.decode("utf-8")

    # Parse for the ReadTheDocs slug
    search_results: parse.Result = parse.search(
        "https://readthedocs.org/projects/{slug:S}/badge", readme_text
    )
    rtd_slug = search_results.named["slug"]

    # GET the latest documentation build runs
    url = f"https://readthedocs.org/api/v3/projects/{rtd_slug}/builds/"
    headers = {"Authorization": f"token {rtd_token}"}
    response = requests.get(url, headers=headers)
    json_response: dict[str, Any] = response.json()

    # Return the results of the latest run
    doc_build_results: Optional[list[dict[str, Any]]] = json_response.get(
        "results", None
    )
    if doc_build_results is None:
        return None
    return doc_build_results[0].get("success")


def check_docs_statuses(
    gh_token: str, rtd_token: str
) -> list[RemoteLibFunc_IterResult[Optional[bool]]]:
    """Checks all the libraries in a cloned Adafruit CircuitPython Bundle
    to get the latest documentation build status with the requested
    information

    .. note::

        The ReadTheDocs token must have sufficient privileges for accessing
        the API; therefore, only a maintainer can use this functionality.

    :param str gh_token: The Github token to be used for with the Github
        API
    :param str rtd_token: A ReadTheDocs API token with sufficient privileges
    :return: A list of tuples containing paired Repository objects and
        documentation build statuses
    :rtype: list
    """

    args = (rtd_token,)
    kwargs = {}
    return iter_remote_bundle_with_func(gh_token, [(check_docs_status, args, kwargs)])
