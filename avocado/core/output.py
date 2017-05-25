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
import errno
import logging
import os
import re
import sys

from . import exit_codes
from ..utils import path as utils_path
from .settings import settings

if hasattr(logging, 'NullHandler'):
    NULL_HANDLER = logging.NullHandler
else:
    import logutils
    NULL_HANDLER = logutils.NullHandler


#: Pre-defined Avocado human UI logger
LOG_UI = logging.getLogger("avocado.app")
#: Pre-defined Avocado job/test logger
LOG_JOB = logging.getLogger("avocado.test")

#: Builtin special keywords to enable set of logging streams
BUILTIN_STREAMS = {'app': 'application output',
                   'test': 'test output',
                   'debug': 'tracebacks and other debugging info',
                   'remote': 'fabric/paramiko debug',
                   'early':  'early logging of other streams, including test (very verbose)'}
#: Groups of builtin streams
BUILTIN_STREAM_SETS = {'all': 'all builtin streams',
                       'none': 'disables regular output (leaving only errors enabled)'}
#: Transparently handles colored terminal, when one is used
TERM_SUPPORT = None
#: Allows modifying the sys.stdout/sys.stderr
STD_OUTPUT = None


class TermSupport(object):

    COLOR_BLUE = '\033[94m'
    COLOR_GREEN = '\033[92m'
    COLOR_YELLOW = '\033[93m'
    COLOR_RED = '\033[91m'
    COLOR_DARKGREY = '\033[90m'

    CONTROL_END = '\033[0m'

    MOVE_BACK = '\033[1D'
    MOVE_FORWARD = '\033[1C'

    ESCAPE_CODES = [COLOR_BLUE, COLOR_GREEN, COLOR_YELLOW, COLOR_RED,
                    COLOR_DARKGREY, CONTROL_END, MOVE_BACK, MOVE_FORWARD]

    """
    Class to help applications to colorize their outputs for terminals.

    This will probe the current terminal and colorize output only if the
    stdout is in a tty or the terminal type is recognized.
    """

    def __init__(self):
        self.HEADER = self.COLOR_BLUE
        self.PASS = self.COLOR_GREEN
        self.SKIP = self.COLOR_YELLOW
        self.FAIL = self.COLOR_RED
        self.INTERRUPT = self.COLOR_RED
        self.ERROR = self.COLOR_RED
        self.WARN = self.COLOR_YELLOW
        self.CANCEL = self.COLOR_YELLOW
        self.PARTIAL = self.COLOR_YELLOW
        self.ENDC = self.CONTROL_END
        self.LOWLIGHT = self.COLOR_DARKGREY
        self.enabled = True
        allowed_terms = ['linux', 'xterm', 'xterm-256color', 'vt100', 'screen',
                         'screen-256color', 'screen.xterm-256color']
        term = os.environ.get("TERM")
        colored = settings.get_value('runner.output', 'colored',
                                     key_type='bool', default=True)
        if not colored or not os.isatty(1) or term not in allowed_terms:
            self.disable()

    def disable(self):
        """
        Disable colors from the strings output by this class.
        """
        self.enabled = False
        self.HEADER = ''
        self.PASS = ''
        self.SKIP = ''
        self.FAIL = ''
        self.INTERRUPT = ''
        self.ERROR = ''
        self.WARN = ''
        self.CANCEL = ''
        self.PARTIAL = ''
        self.ENDC = ''
        self.LOWLIGHT = ''
        self.MOVE_BACK = ''
        self.MOVE_FORWARD = ''

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

    def warn_header_str(self, msg):
        """
        Print a warning header string (yellow colored).

        If the output does not support colors, just return the original string.
        """
        return self.WARN + msg + self.ENDC

    def healthy_str(self, msg):
        """
        Print a healthy string (green colored).

        If the output does not support colors, just return the original string.
        """
        return self.PASS + msg + self.ENDC

    def partial_str(self, msg):
        """
        Print a string that denotes partial progress (yellow colored).

        If the output does not support colors, just return the original string.
        """
        return self.PARTIAL + msg + self.ENDC

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
        Print a error string (red colored).

        If the output does not support colors, just return the original string.
        """
        return self.MOVE_BACK + self.ERROR + 'ERROR' + self.ENDC

    def interrupt_str(self):
        """
        Print an interrupt string (red colored).

        If the output does not support colors, just return the original string.
        """
        return self.MOVE_BACK + self.INTERRUPT + 'INTERRUPT' + self.ENDC

    def warn_str(self):
        """
        Print an warning string (yellow colored).

        If the output does not support colors, just return the original string.
        """
        return self.MOVE_BACK + self.WARN + 'WARN' + self.ENDC


TERM_SUPPORT = TermSupport()


class _StdOutputFile(object):

    """
    File-like object which stores (_is_stdout, content) into the provided list
    """

    def __init__(self, is_stdout, records):
        """
        :param is_stdout: Is this output stdout or stderr
        :param records: list to store (is_stdout, written_message) records
        """
        self._is_stdout = is_stdout
        self._records = records

    def write(self, msg):
        """
        Record the message
        """
        self._records.append((self._is_stdout, msg))

    def writelines(self, iterable):
        """
        Record all messages
        """
        for line in iterable:
            self.write(line)

    def close(self):
        """ File-object methods """
        pass

    def flush(self):
        """ File-object methods """
        pass

    def isatty(self):
        """ File-object methods """
        return False

    def seek(self):
        """ File-object methods """
        pass

    def tell(self):
        """ File-object methods """
        pass

    def getvalue(self):
        """
        Get all messages written to this "file"
        """
        return "\n".join((_[1] for _ in self._records
                          if _[0] == self._is_stdout))


class StdOutput(object):

    """
    Class to modify sys.stdout/sys.stderr
    """
    #: List of records of stored output when stdout/stderr is disabled
    records = []

    def __init__(self):
        self.stdout = self._stdout = sys.stdout
        self.stderr = self._stderr = sys.stderr

    def _paginator_in_use(self):
        """
        :return: True when we output into paginator
        """
        return bool(isinstance(sys.stdout, Paginator))

    def print_records(self):
        """
        Prints all stored messages as they occurred into streams they were
        produced for.
        """
        try:
            for stream, msg in self.records:
                if stream:
                    sys.stdout.write(msg)
                else:
                    sys.stderr.write(msg)
            del self.records[:]
        # IOError due to EPIPE is ignored.  That is to avoid having to
        # handle all IOErrors at the main application loop
        # indiscriminately.  By handling them here, we can be sure
        # that the failure was due to stdout or stderr not being
        # connected to an open PIPE.
        except IOError as e:
            if not e.errno == errno.EPIPE:
                raise

    def fake_outputs(self):
        """
        Replace sys.stdout/sys.stderr with in-memory-objects
        """
        sys.stdout = _StdOutputFile(True, self.records)
        sys.stderr = _StdOutputFile(False, self.records)

    def enable_outputs(self):
        """
        Enable sys.stdout/sys.stderr (either with 2 streams or with paginator)
        """
        sys.stdout = self.stdout
        sys.stderr = self.stderr

    def enable_paginator(self):
        """
        Enable paginator
        """
        self.stdout = self.stderr = Paginator()

    def enable_stderr(self):
        """
        Enable sys.stderr and disable sys.stdout
        """
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = self.stderr

    def close(self):
        """
        Enable original sys.stdout/sys.stderr and cleanup
        """
        paginator = None
        if self._paginator_in_use():
            paginator = sys.stdout
        self.enable_outputs()
        if paginator:
            paginator.close()


STD_OUTPUT = StdOutput()


def early_start():
    """
    Replace all outputs with in-memory handlers
    """
    if os.environ.get('AVOCADO_LOG_DEBUG'):
        add_log_handler(LOG_UI.getChild("debug"), logging.StreamHandler,
                        sys.stdout, logging.DEBUG)
    if os.environ.get('AVOCADO_LOG_EARLY'):
        add_log_handler("", logging.StreamHandler, sys.stdout, logging.DEBUG)
        add_log_handler(LOG_JOB, logging.StreamHandler, sys.stdout,
                        logging.DEBUG)
    else:
        STD_OUTPUT.fake_outputs()
        add_log_handler("", MemStreamHandler, None, logging.DEBUG)
    logging.root.level = logging.DEBUG


def reconfigure(args):
    """
    Adjust logging handlers accordingly to app args and re-log messages.
    """
    # Reconfigure stream loggers
    enabled = getattr(args, "show", None)
    if not isinstance(enabled, list):
        enabled = ["app"]
        args.show = enabled
    if getattr(args, "show_job_log", False):
        del enabled[:]
        enabled.append("test")
    if getattr(args, "silent", False):
        del enabled[:]
    # "silent" is incompatible with "paginator"
    elif getattr(args, "paginator", False) == "on" and TERM_SUPPORT.enabled:
        STD_OUTPUT.enable_paginator()
    if "none" in enabled:
        del enabled[:]
    elif "all" in enabled:
        enabled.extend([_ for _ in BUILTIN_STREAMS if _ not in enabled])
    if os.environ.get("AVOCADO_LOG_EARLY") and "early" not in enabled:
        enabled.append("early")
    if os.environ.get("AVOCADO_LOG_DEBUG") and "debug" not in enabled:
        enabled.append("debug")
    # TODO: Avocado relies on stdout/stderr on some places, re-log them here
    # for now. This should be removed once we replace them with logging.
    if enabled:
        STD_OUTPUT.enable_outputs()
    else:
        STD_OUTPUT.enable_stderr()
    STD_OUTPUT.print_records()
    if "app" in enabled:
        app_handler = ProgressStreamHandler()
        app_handler.setFormatter(logging.Formatter("%(message)s"))
        app_handler.addFilter(FilterInfoAndLess())
        app_handler.stream = STD_OUTPUT.stdout
        LOG_UI.addHandler(app_handler)
        LOG_UI.propagate = False
        LOG_UI.level = logging.DEBUG
    else:
        disable_log_handler(LOG_UI)
    app_err_handler = ProgressStreamHandler()
    app_err_handler.setFormatter(logging.Formatter("%(message)s"))
    app_err_handler.addFilter(FilterWarnAndMore())
    app_err_handler.stream = STD_OUTPUT.stderr
    LOG_UI.addHandler(app_err_handler)
    LOG_UI.propagate = False
    if not os.environ.get("AVOCADO_LOG_EARLY"):
        LOG_JOB.getChild("stdout").propagate = False
        LOG_JOB.getChild("stderr").propagate = False
        if "early" in enabled:
            add_log_handler("", logging.StreamHandler, STD_OUTPUT.stdout,
                            logging.DEBUG)
            add_log_handler(LOG_JOB, logging.StreamHandler,
                            STD_OUTPUT.stdout, logging.DEBUG)
        else:
            disable_log_handler("")
            disable_log_handler(LOG_JOB)
    if "remote" in enabled:
        add_log_handler("avocado.fabric", stream=STD_OUTPUT.stdout,
                        level=logging.DEBUG)
        add_log_handler("paramiko", stream=STD_OUTPUT.stdout,
                        level=logging.DEBUG)
    else:
        disable_log_handler("avocado.fabric")
        disable_log_handler("paramiko")
    # Not enabled by env
    if not os.environ.get('AVOCADO_LOG_DEBUG'):
        if "debug" in enabled:
            add_log_handler(LOG_UI.getChild("debug"), stream=STD_OUTPUT.stdout)
        else:
            disable_log_handler(LOG_UI.getChild("debug"))

    # Add custom loggers
    for name in [_ for _ in enabled if _ not in BUILTIN_STREAMS.iterkeys()]:
        stream_level = re.split(r'(?<!\\):', name, maxsplit=1)
        name = stream_level[0]
        if len(stream_level) == 1:
            level = logging.DEBUG
        else:
            level = (int(stream_level[1]) if stream_level[1].isdigit()
                     else logging.getLevelName(stream_level[1].upper()))
        try:
            add_log_handler(name, logging.StreamHandler, STD_OUTPUT.stdout,
                            level)
        except ValueError as details:
            LOG_UI.error("Failed to set logger for --show %s:%s: %s.",
                         name, level, details)
            sys.exit(exit_codes.AVOCADO_FAIL)
    # Remove the in-memory handlers
    for handler in logging.root.handlers:
        if isinstance(handler, MemStreamHandler):
            logging.root.handlers.remove(handler)

    # Log early_messages
    for record in MemStreamHandler.log:
        logging.getLogger(record.name).handle(record)


class FilterWarnAndMore(logging.Filter):

    def filter(self, record):
        return record.levelno >= logging.WARN


class FilterInfoAndLess(logging.Filter):

    def filter(self, record):
        return record.levelno <= logging.INFO


class ProgressStreamHandler(logging.StreamHandler):

    """
    Handler class that allows users to skip new lines on each emission.
    """

    def emit(self, record):
        try:
            msg = self.format(record)
            if record.levelno < logging.INFO:   # Most messages are INFO
                pass
            elif record.levelno < logging.WARNING:
                msg = TERM_SUPPORT.header_str(msg)
            elif record.levelno < logging.ERROR:
                msg = TERM_SUPPORT.warn_header_str(msg)
            else:
                msg = TERM_SUPPORT.fail_header_str(msg)
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
        except Exception:
            self.handleError(record)


class MemStreamHandler(logging.StreamHandler):

    """
    Handler that stores all records in self.log (shared in all instances)
    """

    log = []

    def emit(self, record):
        self.log.append(record)

    def flush(self):
        """
        This is in-mem object, it does not require flushing
        """
        pass


class PagerNotFoundError(Exception):
    pass


class Paginator(object):

    """
    Paginator that uses less to display contents on the terminal.

    Contains cleanup handling for when user presses 'q' (to quit less).
    """

    def __init__(self):
        try:
            paginator = "%s -FRX" % utils_path.find_command('less')
        except utils_path.CmdNotFoundError:
            paginator = None

        paginator = os.environ.get('PAGER', paginator)

        if paginator is None:
            self.pipe = sys.stdout
        else:
            self.pipe = os.popen(paginator, 'w')

    def __del__(self):
        self.close()

    def close(self):
        try:
            self.pipe.close()
        except Exception:
            pass

    def write(self, msg):
        try:
            self.pipe.write(msg)
        except Exception:
            pass

    def flush(self):
        if not self.pipe.closed:
            self.pipe.flush()


def add_log_handler(logger, klass=logging.StreamHandler, stream=sys.stdout,
                    level=logging.INFO, fmt='%(name)s: %(message)s'):
    """
    Add handler to a logger.

    :param logger_name: the name of a :class:`logging.Logger` instance, that
                        is, the parameter to :func:`logging.getLogger`
    :param klass: Handler class (defaults to :class:`logging.StreamHandler`)
    :param stream: Logging stream, to be passed as an argument to ``klass``
                   (defaults to ``sys.stdout``)
    :param level: Log level (defaults to `INFO``)
    :param fmt: Logging format (defaults to ``%(name)s: %(message)s``)
    """
    if isinstance(logger, basestring):
        logger = logging.getLogger(logger)
    handler = klass(stream)
    handler.setLevel(level)
    if isinstance(fmt, str):
        fmt = logging.Formatter(fmt=fmt)
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.propagate = False
    return handler


def disable_log_handler(logger):
    if isinstance(logger, basestring):
        logger = logging.getLogger(logger)
    # Handlers might be reused elsewhere, can't delete them
    while logger.handlers:
        logger.handlers.pop()
    logger.handlers.append(NULL_HANDLER())
    logger.propagate = False


class LoggingFile(object):

    """
    File-like object that will receive messages pass them to logging.
    """

    def __init__(self, prefix='', level=logging.DEBUG,
                 logger=[logging.getLogger()]):
        """
        Constructor. Sets prefixes and which logger is going to be used.

        :param prefix - The prefix for each line logged by this object.
        """

        self._prefix = prefix
        self._level = level
        self._buffer = []
        if not isinstance(logger, list):
            logger = [logger]
        self._logger = logger

    def write(self, data):
        """"
        Writes data only if it constitutes a whole line. If it's not the case,
        store it in a buffer and wait until we have a complete line.
        :param data - Raw data (a string) that will be processed.
        """
        # splitlines() discards a trailing blank line, so use split() instead
        data_lines = data.split('\n')
        if len(data_lines) > 1:
            self._buffer.append(data_lines[0])
            self._flush_buffer()
        for line in data_lines[1:-1]:
            self._log_line(line)
        if data_lines[-1]:
            self._buffer.append(data_lines[-1])

    def writelines(self, lines):
        """"
        Writes itertable of lines

        :param lines: An iterable of strings that will be processed.
        """
        for data in lines:
            self.write(data)

    def _log_line(self, line):
        """
        Passes lines of output to the logging module.
        """
        for lg in self._logger:
            lg.log(self._level, self._prefix + line)

    def _flush_buffer(self):
        if self._buffer:
            self._log_line(''.join(self._buffer))
            self._buffer = []

    def flush(self):
        self._flush_buffer()

    def isatty(self):
        return False

    def add_logger(self, logger):
        self._logger.append(logger)

    def rm_logger(self, logger):
        self._logger.remove(logger)


class Throbber(object):

    """
    Produces a spinner used to notify progress in the application UI.
    """
    STEPS = ['-', '\\', '|', '/']
    # Only print a throbber when we're on a terminal
    if TERM_SUPPORT.enabled:
        MOVES = [TERM_SUPPORT.MOVE_BACK + STEPS[0],
                 TERM_SUPPORT.MOVE_BACK + STEPS[1],
                 TERM_SUPPORT.MOVE_BACK + STEPS[2],
                 TERM_SUPPORT.MOVE_BACK + STEPS[3]]
    else:
        MOVES = ['', '', '', '']

    def __init__(self):
        self.position = 0

    def _update_position(self):
        if self.position == (len(self.MOVES) - 1):
            self.position = 0
        else:
            self.position += 1

    def render(self):
        result = self.MOVES[self.position]
        self._update_position()
        return result


def log_plugin_failures(failures):
    """
    Log in the application UI failures to load a set of plugins

    :param failures: a list of load failures, usually coming from a
                     :class:`avocado.core.dispatcher.Dispatcher`
                     attribute `load_failures`
    """
    msg_fmt = 'Failed to load plugin from module "%s": %s'
    silenced = settings.get_value('plugins',
                                  'skip_broken_plugin_notification',
                                  list, [])
    for failure in failures:
        if failure[0].module_name in silenced:
            continue
        LOG_UI.error(msg_fmt, failure[0].module_name,
                     failure[1].__repr__())
