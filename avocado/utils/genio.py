# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# This code was inspired in the autotest project,
# client/shared/utils.py
# Authors: Martin J Bligh <mbligh@google.com>, Andy Whitcroft <apw@shadowen.org>

"""
Avocado generic IO related functions.
"""

import logging
import os
import re

from avocado.utils import crypto

LOG = logging.getLogger(__name__)


class GenIOError(Exception):
    """
    Base Exception Class for all IO exceptions
    """


def ask(question, auto=False):
    """
    Prompt the user with a (y/n) question.

    :param question: Question to be asked
    :type question: str
    :param auto: Whether to return "y" instead of asking the question
    :type auto: bool

    :return: User answer
    :rtype: str
    """
    if auto:
        LOG.info("%s (y/n) y", question)
        return "y"
    return input(f"{question} (y/n) ")


def read_file(filename):
    """
    Read the entire contents of file.

    :param filename: Path to the file.
    :type filename: str

    :return: File contents
    :rtype: str
    """
    with open(filename, 'r', encoding='utf-8') as file_obj:
        contents = file_obj.read()
    return contents


def read_one_line(filename):
    """
    Read the first line of filename.

    :param filename: Path to the file.
    :type filename: str

    :return: First line contents
    :rtype: str
    """
    with open(filename, 'r', encoding='utf-8') as file_obj:
        line = file_obj.readline().rstrip('\n')
    return line


def read_all_lines(filename):
    """
    Return all lines of a given file

    This utility method returns an empty list in any error scenario,
    that is, it doesn't attempt to identify error paths and raise
    appropriate exceptions. It does exactly the opposite to that.

    This should be used when it's fine or desirable to have an empty
    set of lines if a file is missing or is unreadable.

    :param filename: Path to the file.
    :type filename: str

    :return: all lines of the file as list
    :rtype: builtin.list
    """
    contents = []
    try:
        with open(filename, 'r', encoding='utf-8') as file_obj:
            contents = [line.rstrip('\n') for line in file_obj.readlines()]
    except Exception:  # pylint: disable=W0703
        pass
    return contents


def write_file(filename, data):
    """
    Write data to a file.

    :param filename: Path to the file.
    :type filename: str
    :param line: Line to be written.
    :type line: str
    """
    with open(filename, 'w', encoding='utf-8') as file_obj:
        file_obj.write(data)


def write_one_line(filename, line):
    """
    Write one line of text to filename.

    :param filename: Path to the file.
    :type filename: str
    :param line: Line to be written.
    :type line: str
    """
    write_file(filename, line.rstrip('\n') + '\n')


def write_file_or_fail(filename, data):
    """
    Write to a file and raise exception on write failure

    :param filename: Path to file
    :type filename: str
    :param data: Data to be written to file
    :type data: str
    :raises GenIOError: On write Failure
    """
    try:
        with open(filename, 'w', encoding='utf-8') as file_obj:
            file_obj.write(data)
    except OSError as details:
        raise GenIOError(f"The write to {filename} failed: {details}")


def append_file(filename, data):
    """
    Append data to a file.

    :param filename: Path to the file.
    :type filename: str
    :param line: Line to be written.
    :type line: str
    """
    with open(filename, 'a+', encoding='utf-8') as file_obj:
        file_obj.write(data)


def append_one_line(filename, line):
    """
    Append one line of text to filename.

    :param filename: Path to the file.
    :type filename: str
    :param line: Line to be written.
    :type line: str
    """
    append_file(filename, line.rstrip('\n') + '\n')


def is_pattern_in_file(filename,  pattern):
    """
    Check if a pattern matches in a specified file. If a non
    regular file be informed a GenIOError will be raised.

    :param filename: Path to file
    :type filename: str
    :param pattern: Pattern that need to match in file
    :type pattern: str
    :return: True when pattern matches in file if not
             return False
    :rtype: boolean
    """
    if not os.path.isfile(filename):
        raise GenIOError(f'invalid file {filename} '
                         f'to match pattern {pattern}')
    with open(filename, 'r', encoding='utf-8') as content_file:
        if re.search(pattern, content_file.read(), re.MULTILINE):
            return True
    return False


def are_files_equal(filename, other):
    """
    Comparison of two files line by line
    :param filename: path to the first file
    :type filename: str
    :param other: path to the second file
    :type other: str
    :return: equality of file
    :rtype: boolean
    """
    hash_1 = crypto.hash_file(filename)
    hash_2 = crypto.hash_file(other)
    return hash_1 == hash_2
