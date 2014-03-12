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


class Bcolors(object):

    """
    Very simple class with color support.
    """

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
        allowed_terms = ['linux', 'xterm', 'xterm-256color', 'vt100',
                         'screen', 'screen-256color']
        term = os.environ.get("TERM")
        if (not os.isatty(1)) or (not term in allowed_terms):
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


class OutputManager(object):

    """
    Takes care of both disk logs and stdout/err logs.
    """

    def __init__(self, logger_name='avocado.app'):
        self.colors = Bcolors()

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
        header_msg = self.colors.HEADER + sr + self.colors.ENDC
        self.info(header_msg)

    def log_pass(self, label, t_elapsed):
        normal_pass_msg = (label + " " + self.colors.PASS + "PASS" +
                           self.colors.ENDC + " (%.2f s)" % t_elapsed)
        self.info(normal_pass_msg)

    def log_fail(self, label, t_elapsed):
        normal_fail_msg = (label + " " + self.colors.FAIL + "FAIL" +
                           self.colors.ENDC + " (%.2f s)" % t_elapsed)
        self.error(normal_fail_msg)

    def log_skip(self, label, t_elapsed):
        normal_skip_msg = (label + " " + self.colors.SKIP + "SKIP" +
                           self.colors.ENDC)
        self.info(normal_skip_msg)

    def log_warn(self, label, t_elapsed):
        normal_warn_msg = (label + " " + self.colors.WARN + "WARN" +
                           self.colors.ENDC + " (%.2f s)" % t_elapsed)
        self.error(normal_warn_msg)
