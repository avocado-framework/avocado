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
import resource


log = logging.getLogger('avocado.test')


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


class CoreGeneratorConfig(object):

    """
    Configures the system for automatic `core` file generation
    """

    def __init__(self):
        self.previous_core_soft_limit = None
        self.previous_core_hard_limit = None
        self.previous_core_pattern = None
        self.enabled = None

    def enable(self):
        """
        Runs all necessary actions to enable core files

        Together with `disable()` this is this class' primary interface
        """
        (self.previous_core_soft_limit,
         self.previous_core_hard_limit) = self.get_limits()

        self.set_limits()

    def disable(self):
        """
        Runs all necessary actions to disable core files

        Together with `enable()` this is this class' primary interface
        """
        self.set_limits(self.previous_core_soft_limit,
                        self.previous_core_hard_limit)

        (new_soft_limit,
         new_hard_limit) = self.get_limits()

        assert self.previous_core_soft_limit == new_soft_limit
        assert self.previous_core_hard_limit == new_hard_limit

    def get_limits(self):
        """
        Get the current value for generated core files size limit

        :returns: the current soft and hard limit, both as integers
        :rtype: tuple
        """
        return resource.getrlimit(resource.RLIMIT_CORE)

    def set_limits(self,
                   soft=resource.RLIM_INFINITY,
                   hard=resource.RLIM_INFINITY):
        """
        Configures the current user core file size limit
        """
        resource.setrlimit(resource.RLIMIT_CORE, (soft, hard))

    def set_core_pattern(self):
        """
        Configures the `kernel.core_pattern` system tunable

        So that core dumps are generated within a test data directory
        """
        pass
