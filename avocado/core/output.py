"""
Manages output and logging in avocado applications.
"""
import logging
import os
import sys

class StreamProxy(object):

    """
    Mechanism to redirect a stream to a file, allowing the original stream to
    be restored later.
    """

    def __init__(self, filename='/dev/null', stream=sys.stdout):
        """
        Keep 2 streams to write to, and eventually switch.
        """
        self.terminal = stream
        if filename is None:
            self.log = stream
        else:
            self.log = open(filename, "a")
        self.redirect()

    def write(self, message):
        """
        Write to the current stream.
        """
        self.stream.write(message)

    def flush(self):
        """
        Flush the current stream.
        """
        self.stream.flush()

    def restore(self):
        """Restore original stream"""
        self.stream = self.terminal

    def redirect(self):
        """Redirect stream to log file"""
        self.stream = self.log


def _silence_stderr():
    """
    Points the stderr FD (2) to /dev/null, silencing it.
    """
    out_fd = os.open('/dev/null', os.O_WRONLY | os.O_CREAT)
    try:
        os.dup2(out_fd, 2)
    finally:
        os.close(out_fd)
    sys.stderr = os.fdopen(2, 'w')


def _handle_stdout(options):
    """
    Replace stdout with a proxy object.

    Depending on self.options.verbose, make proxy print to /dev/null, or
    original sys.stdout stream.
    """
    if not options.verbose:
        _silence_stderr()
        # Replace stdout with our proxy pointing to /dev/null
        sys.stdout = StreamProxy(filename="/dev/null", stream=sys.stdout)
    else:
        # Retain full stdout
        sys.stdout = StreamProxy(filename=None, stream=sys.stdout)


def _restore_stdout():
    """
    Restore stdout. Used to re-enable stdout on error paths.
    """
    try:
        sys.stdout.restore()
    except AttributeError:
        pass


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
    def __init__(self, logger_name='avocado.utils'):
        self.colors = Bcolors()
        self.log = logging.getLogger(logger_name)

    def _log(self, sr, level=logging.INFO):
        self.log.log(level, sr)

    def create_file_handler(self, logfile, level=logging.DEBUG):
        """
        Simple helper for adding a file logger to the root logger.
        """
        file_handler = logging.FileHandler(filename=logfile)
        file_handler.setLevel(level)

        fmt = '%(asctime)s %(levelname)-5.5s| %(message)s'
        formatter = logging.Formatter(fmt=fmt, datefmt='%H:%M:%S')

        file_handler.setFormatter(formatter)
        self.log.addHandler(file_handler)
        return file_handler

    def remove_file_handler(self, handler):
        """
        Simple helper for removing a handler from the current logger.
        """
        self.log.removeHandler(handler)
        handler.close()

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
