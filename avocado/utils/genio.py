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
# Authors: Martin J Bligh <mbligh@google.com>
#          Andy Whitcroft <apw@shadowen.org>
#
# Modification History:
# - Added read_line_with_matching_pattern()

"""Avocado generic IO related functions."""

import logging
import os
import re

from avocado.utils import crypto

LOG = logging.getLogger(__name__)


class GenIOError(Exception):
    """Base Exception Class for all IO exceptions."""


def ask(question, auto=False):
    """Prompt the user with a (y/n) question.

    :param question: Question to be asked.
    :type question: str
    :param auto: Whether to return "y" instead of asking the question.
    :type auto: bool
    :return: User answer.
    :rtype: str

    Example::

        >>> ask("Do you want to continue?", auto=True)
        'y'
    """
    if auto:
        LOG.info("%s (y/n) y", question)
        return "y"
    return input(f"{question} (y/n) ")


def read_file(filename):
    """Read the entire contents of a file.

    :param filename: Path to the file.
    :type filename: str
    :return: File contents.
    :rtype: str
    :raises FileNotFoundError: When the file does not exist.
    :raises PermissionError: When the file cannot be read due to permissions.

    Example::

        >>> read_file("/etc/hostname")  # doctest: +SKIP
        'myhost\\n'
    """
    with open(filename, "r", encoding="utf-8") as file_obj:
        contents = file_obj.read()
    return contents


def read_one_line(filename):
    """Read the first line of a file.

    The returned line has the trailing newline character stripped.

    :param filename: Path to the file.
    :type filename: str
    :return: First line contents with newline stripped.
    :rtype: str
    :raises FileNotFoundError: When the file does not exist.
    :raises PermissionError: When the file cannot be read due to permissions.

    Example::

        >>> read_one_line("/etc/hostname")  # doctest: +SKIP
        'myhost'
    """
    with open(filename, "r", encoding="utf-8") as file_obj:
        line = file_obj.readline().rstrip("\n")
    return line


def read_all_lines(filename):
    """Return all lines of a given file.

    This utility method returns an empty list in any error scenario,
    that is, it doesn't attempt to identify error paths and raise
    appropriate exceptions. It does exactly the opposite to that.

    This should be used when it's fine or desirable to have an empty
    set of lines if a file is missing or is unreadable.

    :param filename: Path to the file.
    :type filename: str
    :return: All lines of the file as a list with newlines stripped.
    :rtype: list

    Example::

        >>> read_all_lines("/etc/hosts")  # doctest: +SKIP
        ['127.0.0.1 localhost', '::1 localhost']
        >>> read_all_lines("/nonexistent/file.txt")
        []
    """
    contents = []
    try:
        with open(filename, "r", encoding="utf-8") as file_obj:
            contents = [line.rstrip("\n") for line in file_obj.readlines()]
    except Exception:  # pylint: disable=W0703
        pass
    return contents


def read_line_with_matching_pattern(filename, pattern):
    """Return lines from a file that contain a given pattern.

    This method returns all lines where the pattern substring is found.
    The search uses simple substring matching (not regex).

    :param filename: Path to the file to be read.
    :type filename: str
    :param pattern: Pattern substring to search for in each line.
    :type pattern: str
    :return: All lines from the file that contain the pattern, with newlines stripped.
    :rtype: list
    :raises FileNotFoundError: When the file does not exist.
    :raises PermissionError: When the file cannot be read due to permissions.

    Example::

        >>> read_line_with_matching_pattern("/etc/passwd", "root")  # doctest: +SKIP
        ['root:x:0:0:root:/root:/bin/bash']
    """
    contents = []
    with open(filename, "r", encoding="utf-8") as file_obj:
        for line in file_obj.readlines():
            if pattern in line:
                contents.append(line.rstrip("\n"))
    return contents


def write_file(filename, data):
    """Write data to a file.

    This will overwrite any existing content in the file. If the file
    does not exist, it will be created.

    :param filename: Path to the file.
    :type filename: str
    :param data: Data to be written to the file.
    :type data: str
    :raises FileNotFoundError: When the parent directory does not exist.
    :raises PermissionError: When the file cannot be written due to permissions.

    Example::

        >>> write_file("/tmp/test.txt", "Hello World")  # doctest: +SKIP
    """
    with open(filename, "w", encoding="utf-8") as file_obj:
        file_obj.write(data)


def write_one_line(filename, line):
    """Write one line of text to a file.

    A newline character is automatically appended. Any existing trailing
    newline in the input line is stripped before adding the newline.

    :param filename: Path to the file.
    :type filename: str
    :param line: Line to be written.
    :type line: str
    :raises FileNotFoundError: When the parent directory does not exist.
    :raises PermissionError: When the file cannot be written due to permissions.

    Example::

        >>> write_one_line("/tmp/test.txt", "Hello World")  # doctest: +SKIP
    """
    write_file(filename, line.rstrip("\n") + "\n")


def write_file_or_fail(filename, data):
    """Write to a file and raise GenIOError on write failure.

    Unlike :func:`write_file`, this function catches OSError exceptions
    and re-raises them as GenIOError with a descriptive message.

    :param filename: Path to the file.
    :type filename: str
    :param data: Data to be written to the file.
    :type data: str
    :raises GenIOError: When the write operation fails for any reason.

    Example::

        >>> write_file_or_fail("/tmp/test.txt", "Hello World")  # doctest: +SKIP
    """
    try:
        with open(filename, "w", encoding="utf-8") as file_obj:
            file_obj.write(data)
    except OSError as details:
        raise GenIOError(f"The write to {filename} failed: {details}") from details


def append_file(filename, data):
    """Append data to a file.

    If the file does not exist, it will be created.

    :param filename: Path to the file.
    :type filename: str
    :param data: Data to be appended to the file.
    :type data: str
    :raises FileNotFoundError: When the parent directory does not exist.
    :raises PermissionError: When the file cannot be written due to permissions.

    Example::

        >>> append_file("/tmp/log.txt", "New log entry\\n")  # doctest: +SKIP
    """
    with open(filename, "a+", encoding="utf-8") as file_obj:
        file_obj.write(data)


def append_one_line(filename, line):
    """Append one line of text to a file.

    A newline character is automatically appended. Any existing trailing
    newline in the input line is stripped before adding the newline.
    If the file does not exist, it will be created.

    :param filename: Path to the file.
    :type filename: str
    :param line: Line to be appended.
    :type line: str
    :raises FileNotFoundError: When the parent directory does not exist.
    :raises PermissionError: When the file cannot be written due to permissions.

    Example::

        >>> append_one_line("/tmp/log.txt", "Log entry 1")  # doctest: +SKIP
        >>> append_one_line("/tmp/log.txt", "Log entry 2")  # doctest: +SKIP
    """
    append_file(filename, line.rstrip("\n") + "\n")


def is_pattern_in_file(filename, pattern):
    """Check if a regex pattern matches anywhere in a file.

    The pattern is matched using Python's re.search with MULTILINE mode,
    allowing patterns like ``^`` and ``$`` to match at line boundaries.

    :param filename: Path to the file.
    :type filename: str
    :param pattern: Regular expression pattern to search for.
    :type pattern: str
    :return: True if pattern matches anywhere in the file, False otherwise.
    :rtype: bool
    :raises GenIOError: When filename is not a regular file (e.g., directory).

    Example::

        >>> is_pattern_in_file("/etc/passwd", r"^root:")  # doctest: +SKIP
        True
        >>> is_pattern_in_file("/etc/passwd", r"nonexistent")  # doctest: +SKIP
        False
    """
    if not os.path.isfile(filename):
        raise GenIOError(f"invalid file {filename} " f"to match pattern {pattern}")
    with open(filename, "r", encoding="utf-8") as content_file:
        if re.search(pattern, content_file.read(), re.MULTILINE):
            return True
    return False


def are_files_equal(filename, other):
    """Compare two files for equality using cryptographic hashing.

    This function computes the hash of both files and compares them,
    which is efficient for large files. Files are considered equal
    if they have identical content.

    :param filename: Path to the first file.
    :type filename: str
    :param other: Path to the second file.
    :type other: str
    :return: True if files have identical content, False otherwise.
    :rtype: bool

    Example::

        >>> are_files_equal("/tmp/file1.txt", "/tmp/file2.txt")  # doctest: +SKIP
        True
    """
    hash_1 = crypto.hash_file(filename)
    hash_2 = crypto.hash_file(other)
    return hash_1 == hash_2


# pylint: disable=wrong-import-position
from avocado.utils.deprecation import log_deprecation

log_deprecation.warning(
    "genio",
    "The genio utility is deprecated and will be removed after the next LTS release.",
)
