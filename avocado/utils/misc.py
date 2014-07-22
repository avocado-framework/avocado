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

import logging

log = logging.getLogger('avocado.test')


def ask(question, auto=False):
    """
    Raw input with a prompt.

    :param question: Question to be asked
    :param auto: Whether to return "y" instead of asking the question
    """
    if auto:
        log.info("%s (y/n) y" % question)
        return "y"
    return raw_input("%s (y/n) " % question)


def read_file(filename):
    """
    Read the entire contents of file.

    :param filename: Path to the file.
    """
    with open(filename, 'r') as file_obj:
        contents = file_obj.read()
    return contents

    f = open(filename)
    try:
        return f.read()
    finally:
        f.close()


def read_one_line(filename):
    """
    Read the first line of filename.

    :param filename: Path to the file.
    """
    with open(filename, 'r') as file_obj:
        line = file_obj.readline().rstrip('\n')
    return line


def write_one_line(filename, line):
    """
    Write one line of text to filename.

    :param filename: Path to the file.
    :param line: Line to be written.
    """
    write_file(filename, line.rstrip('\n') + '\n')


def write_file(filename, data):
    """
    Write data to a file.

    :param filename: Path to the file.
    :param line: Line to be written.
    """
    with open(filename, 'w') as file_obj:
        file_obj.write(data)
