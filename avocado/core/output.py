"""
Manages output and logging in avocado applications.
"""
import logging
import os
import sys

from avocado.utils import process


def get_paginator():
    try:
        less_cmd = process.find_command('less')
        return os.popen('%s -FRSX' % less_cmd, 'w')
    except ValueError:
        return sys.stdout


def add_console_handler(logger):
    """
    Add a console handler to a logger.
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
        if (not os.isatty(1)) or (not term in self.allowed_terms):
            self.disable()

    def disable(self):
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
        return self.HEADER + sr + self.ENDC

    def pass_str(self):
        return self.PASS + 'PASS' + self.ENDC

    def skip_str(self):
        return self.SKIP + 'SKIP' + self.ENDC

    def fail_str(self):
        return self.FAIL + 'FAIL' + self.ENDC

    def error_str(self):
        return self.ERROR + 'ERROR' + self.ENDC

    def warn_str(self):
        return self.WARN + 'WARN' + self.ENDC


colors = TermColors()


class OutputManager(object):

    """
    Takes care of both disk logs and stdout/err logs.
    """

    def __init__(self, logger_name='avocado.app'):
        self.console_log = logging.getLogger('avocado.app')

    def _log(self, sr, level=logging.INFO):
        self.console_log.log(level, sr)

    def start_file_logging(self, logfile, level):
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
        self._log(sr, level=logging.INFO)

    def error(self, sr):
        self._log(sr, level=logging.ERROR)

    def log_header(self, sr):
        self.info(colors.header_str(sr))

    def log_pass(self, label, t_elapsed):
        normal_pass_msg = (label + " " + colors.pass_str() +
                           " (%.2f s)" % t_elapsed)
        self.info(normal_pass_msg)

    def log_fail(self, label, t_elapsed):
        normal_fail_msg = (label + " " + colors.fail_str() +
                           " (%.2f s)" % t_elapsed)
        self.error(normal_fail_msg)

    def log_skip(self, label, t_elapsed):
        normal_skip_msg = (label + " " + colors.skip_str())
        self.info(normal_skip_msg)

    def log_warn(self, label, t_elapsed):
        normal_warn_msg = (label + " " + colors.warn_str() +
                           " (%.2f s)" % t_elapsed)
        self.error(normal_warn_msg)
