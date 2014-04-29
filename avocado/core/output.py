# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Manages output and logging in avocado applications.
"""
import logging
import os
import sys

from avocado.utils import process


def get_paginator():
    """
    Get a pipe. If we can't do that, return stdout.

    The paginator is 'less'. The paginator is a useful feature inspired in
    programs such as git, since it lets you scroll up and down large buffers
    of text, increasing the program's usability.
    """
    try:
        less_cmd = process.find_command('less')
        return os.popen('%s -FRSX' % less_cmd, 'w')
    except ValueError:
        return sys.stdout


def add_console_handler(logger):
    """
    Add a console handler to a logger.

    :param logger: `logging.Logger` instance.
    """
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(fmt='%(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


class TermColors(object):

    """
    Class to help applications to colorize their outputs for terminals.

    This will probe the current terminal and colorize ouput only if the
    stdout is in a tty or the terminal type is recognized.
    """

    allowed_terms = ['linux', 'xterm', 'xterm-256color', 'vt100', 'screen',
                     'screen-256color']

    def __init__(self):
        self.blue = '\033[94m'
        self.green = '\033[92m'
        self.yellow = '\033[93m'
        self.red = '\033[91m'
        self.end = '\033[0m'
        self.HEADER = self.blue
        self.PASS = self.green
        self.SKIP = self.yellow
        self.FAIL = self.red
        self.ERROR = self.red
        self.WARN = self.yellow
        self.ENDC = self.end
        term = os.environ.get("TERM")
        if (not os.isatty(1)) or (term not in self.allowed_terms):
            self.disable()

    def disable(self):
        """
        Disable colors from the strings output by this class.
        """
        self.blue = ''
        self.green = ''
        self.yellow = ''
        self.red = ''
        self.end = ''
        self.HEADER = ''
        self.PASS = ''
        self.SKIP = ''
        self.FAIL = ''
        self.ERROR = ''
        self.WARN = ''
        self.ENDC = ''

    def header_str(self, sr):
        """
        Print a header string (blue colored).

        If the output does not support colors, just return the original string.
        """
        return self.HEADER + sr + self.ENDC

    def pass_str(self):
        """
        Print a pass string (green colored).

        If the output does not support colors, just return the original string.
        """
        return self.PASS + 'PASS' + self.ENDC

    def skip_str(self):
        """
        Print a skip string (yellow colored).

        If the output does not support colors, just return the original string.
        """
        return self.SKIP + 'SKIP' + self.ENDC

    def fail_str(self):
        """
        Print a fail string (red colored).

        If the output does not support colors, just return the original string.
        """
        return self.FAIL + 'FAIL' + self.ENDC

    def error_str(self):
        """
        Print an error string (red colored).

        If the output does not support colors, just return the original string.
        """
        return self.ERROR + 'ERROR' + self.ENDC

    def warn_str(self):
        """
        Print an warning string (yellow colored).

        If the output does not support colors, just return the original string.
        """
        return self.WARN + 'WARN' + self.ENDC


colors = TermColors()


class OutputManager(object):

    """
    Takes care of both disk logs and stdout/err logs.
    """

    def __init__(self, logger_name='avocado.app'):
        self.console_log = logging.getLogger('avocado.app')

    def _log(self, sr, level=logging.INFO):
        """
        Write a message to the avocado.app logger.

        :param sr: String to write.
        """
        self.console_log.log(level, sr)

    def start_file_logging(self, logfile, level):
        """
        Start the main file logging.

        :param logfile: Path to file that will receive logging.
        :param level: Level of the logger. Example: :mod:`logging.DEBUG`.
        """
        self.file_handler = logging.FileHandler(filename=logfile)
        self.file_handler.setLevel(level)

        fmt = '%(asctime)s %(module)-10.10s L%(lineno)-.4d %(levelname)-5.5s| %(message)s'
        formatter = logging.Formatter(fmt=fmt, datefmt='%H:%M:%S')

        self.file_handler.setFormatter(formatter)
        test_logger = logging.getLogger('avocado.test')
        utils_logger = logging.getLogger('avocado.utils')
        linux_logger = logging.getLogger('avocado.linux')
        test_logger.addHandler(self.file_handler)
        utils_logger.addHandler(self.file_handler)
        linux_logger.addHandler(self.file_handler)

    def stop_file_logging(self):
        """
        Simple helper for removing a handler from the current logger.
        """
        test_logger = logging.getLogger('avocado.test')
        utils_logger = logging.getLogger('avocado.utils')
        linux_logger = logging.getLogger('avocado.linux')
        test_logger.removeHandler(self.file_handler)
        utils_logger.removeHandler(self.file_handler)
        linux_logger.removeHandler(self.file_handler)
        self.file_handler.close()

    def info(self, sr):
        """
        Log a :mod:`logging.INFO` message.

        :param sr: String to write.
        """
        self._log(sr, level=logging.INFO)

    def error(self, sr):
        """
        Log a :mod:`logging.INFO` message.

        :param sr: String to write.
        """
        self._log(sr, level=logging.ERROR)

    def log_header(self, sr):
        """
        Log a header message.

        :param sr: String to write.
        """
        self.info(colors.header_str(sr))

    def log_pass(self, label, t_elapsed):
        """
        Log a test PASS message.

        :param label: Label for the PASS message (test name + index).
        :param t_elapsed: Time it took for test to complete.
        """
        normal_pass_msg = (label + " " + colors.pass_str() +
                           " (%.2f s)" % t_elapsed)
        self.info(normal_pass_msg)

    def log_error(self, label, t_elapsed):
        """
        Log a test ERROR message.

        :param label: Label for the FAIL message (test name + index).
        :param t_elapsed: Time it took for test to complete.
        """
        normal_error_msg = (label + " " + colors.error_str() +
                            " (%.2f s)" % t_elapsed)
        self.error(normal_error_msg)

    def log_fail(self, label, t_elapsed):
        """
        Log a test FAIL message.

        :param label: Label for the FAIL message (test name + index).
        :param t_elapsed: Time it took for test to complete.
        """
        normal_fail_msg = (label + " " + colors.fail_str() +
                           " (%.2f s)" % t_elapsed)
        self.error(normal_fail_msg)

    def log_skip(self, label, t_elapsed):
        """
        Log a test SKIP message.

        :param label: Label for the SKIP message (test name + index).
        :param t_elapsed: Time it took for test to complete.
        """
        normal_skip_msg = (label + " " + colors.skip_str())
        self.info(normal_skip_msg)

    def log_warn(self, label, t_elapsed):
        """
        Log a test WARN message.

        :param label: Label for the WARN message (test name + index).
        :param t_elapsed: Time it took for test to complete.
        """
        normal_warn_msg = (label + " " + colors.warn_str() +
                           " (%.2f s)" % t_elapsed)
        self.error(normal_warn_msg)
