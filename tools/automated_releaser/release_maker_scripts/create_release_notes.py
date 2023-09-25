# SPDX-FileCopyrightText: 2023 Tim Cocks
#
# SPDX-License-Identifier: MIT

"""
Create release_notes.md file populated with appropriate message for the
given library.
"""
from jinja2 import Template


def create_release_notes(pypi_name):
    """
    render the release notes into a md file.
    """
    with open("templates/release_notes_template.md", "r") as f:
        release_notes_template = Template(f.read())

    _rendered_template_text = release_notes_template.render(pypi_name=pypi_name)

    with open("release_notes.md", "w") as f:
        f.write(_rendered_template_text)


if __name__ == "__main__":
    create_release_notes("testrepo")
