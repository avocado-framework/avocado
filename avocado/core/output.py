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


class ProgressStreamHandler(logging.StreamHandler):

    """
    Handler class that allows users to skip new lines on each emission.
    """

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            skip_newline = False
            if hasattr(record, 'skip_newline'):
                skip_newline = record.skip_newline
            stream.write(msg)
            if not skip_newline:
                stream.write('\n')
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


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
    except process.CmdNotFoundError:
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


class TermSupport(object):

    COLOR_BLUE = '\033[94m'
    COLOR_GREEN = '\033[92m'
    COLOR_YELLOW = '\033[93m'
    COLOR_RED = '\033[91m'

    CONTROL_END = '\033[0m'

    MOVE_BACK = '\033[1D'
    MOVE_FORWARD = '\033[1C'

    """
    Class to help applications to colorize their outputs for terminals.

    This will probe the current terminal and colorize ouput only if the
    stdout is in a tty or the terminal type is recognized.
    """

    allowed_terms = ['linux', 'xterm', 'xterm-256color', 'vt100', 'screen',
                     'screen-256color']

    def __init__(self):
        self.HEADER = self.COLOR_BLUE
        self.PASS = self.COLOR_GREEN
        self.SKIP = self.COLOR_YELLOW
        self.FAIL = self.COLOR_RED
        self.ERROR = self.COLOR_RED
        self.WARN = self.COLOR_YELLOW
        self.ENDC = self.CONTROL_END
        term = os.environ.get("TERM")
        if (not os.isatty(1)) or (term not in self.allowed_terms):
            self.disable()

    def disable(self):
        """
        Disable colors from the strings output by this class.
        """
        self.HEADER = ''
        self.PASS = ''
        self.SKIP = ''
        self.FAIL = ''
        self.ERROR = ''
        self.WARN = ''
        self.ENDC = ''

    def header_str(self, msg):
        """
        Print a header string (blue colored).

        If the output does not support colors, just return the original string.
        """
        return self.HEADER + msg + self.ENDC

    def fail_header_str(self, msg):
        """
        Print a fail header string (red colored).

        If the output does not support colors, just return the original string.
        """
        return self.FAIL + msg + self.ENDC

    def healthy_str(self, msg):
        """
        Print a healthy string (green colored).

        If the output does not support colors, just return the original string.
        """
        return self.PASS + msg + self.ENDC

    def pass_str(self):
        """
        Print a pass string (green colored).

        If the output does not support colors, just return the original string.
        """
        return self.MOVE_BACK + self.PASS + 'PASS' + self.ENDC

    def skip_str(self):
        """
        Print a skip string (yellow colored).

        If the output does not support colors, just return the original string.
        """
        return self.MOVE_BACK + self.SKIP + 'SKIP' + self.ENDC

    def fail_str(self):
        """
        Print a fail string (red colored).

        If the output does not support colors, just return the original string.
        """
        return self.MOVE_BACK + self.FAIL + 'FAIL' + self.ENDC

    def error_str(self):
        """
        Print an error string (red colored).

        If the output does not support colors, just return the original string.
        """
        return self.MOVE_BACK + self.ERROR + 'ERROR' + self.ENDC

    def warn_str(self):
        """
        Print an warning string (yellow colored).

        If the output does not support colors, just return the original string.
        """
        return self.MOVE_BACK + self.WARN + 'WARN' + self.ENDC


term_support = TermSupport()


class OutputManager(object):

    """
    Takes care of both disk logs and stdout/err logs.
    """

    THROBBER_STEPS = ['-', '\\', '|', '/']
    THROBBER_MOVES = [term_support.MOVE_BACK + THROBBER_STEPS[0],
                      term_support.MOVE_BACK + THROBBER_STEPS[1],
                      term_support.MOVE_BACK + THROBBER_STEPS[2],
                      term_support.MOVE_BACK + THROBBER_STEPS[3]]

    def __init__(self, logger_name='avocado.app'):
        self.console_log = logging.getLogger('avocado.app')
        self.throbber_pos = 0

    def throbber_progress(self):
        self.log_healthy(self.THROBBER_MOVES[self.throbber_pos], True)
        if self.throbber_pos == (len(self.THROBBER_MOVES)-1):
            self.throbber_pos = 0
        else:
            self.throbber_pos += 1

    def _log(self, msg, level=logging.INFO, skip_newline=False):
        """
        Write a message to the avocado.app logger.

        :param msg: Message to write
        :type msg: string
        """
        extra = {'skip_newline': skip_newline}
        self.console_log.log(level=level, msg=msg, extra=extra)

    def start_file_logging(self, logfile, loglevel):
        """
        Start the main file logging.

        :param logfile: Path to file that will receive logging.
        :param loglevel: Level of the logger. Example: :mod:`logging.DEBUG`.
        """
        self.debuglog = logfile
        self.file_handler = logging.FileHandler(filename=logfile)
        self.file_handler.setLevel(loglevel)

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

    def info(self, msg, skip_newline=False):
        """
        Log a :mod:`logging.INFO` message.

        :param msg: Message to write.
        """
        self._log(msg, level=logging.INFO, skip_newline=skip_newline)

    def error(self, msg):
        """
        Log a :mod:`logging.INFO` message.

        :param msg: Message to write.
        """
        self._log(msg, level=logging.ERROR)

    def log_healthy(self, msg, skip_newline=False):
        """
        Log a message that indicates something healthy is going on

        :param msg: Message to write.
        """
        self.info(term_support.healthy_str(msg), skip_newline)

    def log_header(self, msg):
        """
        Log a header message.

        :param msg: Message to write.
        """
        self.info(term_support.header_str(msg))

    def log_fail_header(self, msg):
        """
        Log a fail header message (red, for critical errors).

        :param msg: Message to write.
        """
        self.info(term_support.fail_header_str(msg))

    def log_pass(self, t_elapsed):
        """
        Log a PASS message.

        :param t_elapsed: Time it took for the operation to complete.
        """
        normal_pass_msg = term_support.pass_str() + " (%.2f s)" % t_elapsed
        self.info(normal_pass_msg)

    def log_error(self, t_elapsed):
        """
        Log an ERROR message.

        :param t_elapsed: Time it took for the operation to complete.
        """
        normal_error_msg = term_support.error_str() + " (%.2f s)" % t_elapsed
        self.error(normal_error_msg)

    def log_fail(self, t_elapsed):
        """
        Log a FAIL message.

        :param t_elapsed: Time it took for the operation to complete.
        """
        normal_fail_msg = term_support.fail_str() + " (%.2f s)" % t_elapsed
        self.error(normal_fail_msg)

    def log_skip(self, t_elapsed):
        """
        Log a SKIP message.

        :param t_elapsed: Time it took for the operation to complete.
        """
        normal_skip_msg = term_support.skip_str()
        self.info(normal_skip_msg)

    def log_warn(self, t_elapsed):
        """
        Log a WARN message.

        :param t_elapsed: Time it took for the operation to complete.
        """
        normal_warn_msg = term_support.warn_str() + " (%.2f s)" % t_elapsed
        self.error(normal_warn_msg)
