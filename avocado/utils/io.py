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
import time

from avocado.utils import path as apath


log = logging.getLogger('avocado.test')


_open_log_files = {}
_log_file_dir = "/tmp"


def log_line(filename, line):
    """
    Write a line to a file.

    :param filename: Path of file to write to, either absolute or relative to
                     the dir set by set_log_file_dir().
    :param line: Line to write.
    """
    global _open_log_files, _log_file_dir

    path = apath.get_path(_log_file_dir, filename)
    if path not in _open_log_files:
        # First, let's close the log files opened in old directories
        close_log_file(filename)
        # Then, let's open the new file
        try:
            os.makedirs(os.path.dirname(path))
        except OSError:
            pass
        _open_log_files[path] = open(path, "w")
    timestr = time.strftime("%Y-%m-%d %H:%M:%S")
    _open_log_files[path].write("%s: %s\n" % (timestr, line))
    _open_log_files[path].flush()


def set_log_file_dir(directory):
    """
    Set the base directory for log files created by log_line().

    :param dir: Directory for log files.
    """
    global _log_file_dir
    _log_file_dir = directory


def close_log_file(filename):
    global _open_log_files, _log_file_dir
    remove = []
    for k in _open_log_files:
        if os.path.basename(k) == filename:
            f = _open_log_files[k]
            f.close()
            remove.append(k)
    if remove:
        for key_to_remove in remove:
            _open_log_files.pop(key_to_remove)


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
        log.info("%s (y/n) y" % question)
        return "y"
    return raw_input("%s (y/n) " % question)


def read_file(filename):
    """
    Read the entire contents of file.

    :param filename: Path to the file.
    :type filename: str

    :return: File contents
    :rtype: str
    """
    with open(filename, 'r') as file_obj:
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
    with open(filename, 'r') as file_obj:
        line = file_obj.readline().rstrip('\n')
    return line


def write_file(filename, data):
    """
    Write data to a file.

    :param filename: Path to the file.
    :type filename: str
    :param line: Line to be written.
    :type line: str
    """
    with open(filename, 'w') as file_obj:
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
