# The MIT License (MIT)
#
# Copyright (c) 2019 Michael Schroeder
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

import os
import pathlib
import re

import sh
from sh.contrib import git


def board_count():
    """ Retrieve the number of boards currently supported by Adafruit_Blinka,
        via Adafruit_Python_PlatformDetect.
    """
    platdetec_boards_re = re.compile(r'^[A-Z]\w+\s+\=\s[\'\"]\w+[\'\"]',
                                     re.MULTILINE)
    board_count = 0
    working_dir = os.getcwd()
    blinka_dir = pathlib.Path(working_dir, '.blinka')
    repo_url = 'https://github.com/adafruit/Adafruit_Python_PlatformDetect.git'

    if not blinka_dir.exists():
        try:
            git.clone(repo_url, blinka_dir.resolve(), '--depth', '1')
        except sh.ErrorReturnCode_128:
            print("Failed to clone Adafruit_Blinka. Board count not determined.")
            board_count = "Error"

    src_board_path = blinka_dir / 'adafruit_platformdetect/board.py'
    if src_board_path.exists():
        board_content = ""
        with open(src_board_path, 'r') as board_py:
            board_content = board_py.read()
        content_re = platdetec_boards_re.findall(board_content)
        board_count = len(content_re)

    return board_count
