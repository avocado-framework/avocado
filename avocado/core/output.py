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
import traceback

from avocado.core import exit_codes
from avocado.core.settings import settings
from avocado.core.streams import BUILTIN_STREAMS
from avocado.utils import path as utils_path

#: Handle cases of logging exceptions which will lead to recursion error
logging.raiseExceptions = False

#: Pre-defined Avocado human UI logger
LOG_UI = logging.getLogger("avocado.app")
#: Pre-defined Avocado job/test logger
LOG_JOB = logging.getLogger("avocado.test")


class TermSupport:

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
        config = settings.as_dict()
        colored = config.get('runner.output.colored')
        force_color = config.get('runner.output.color')
        if force_color == "never":
            self.disable()
        elif force_color == "auto":
            if not colored or not os.isatty(1) or term not in allowed_terms:
                self.disable()
        elif force_color != "always":
            raise ValueError("The value for runner.output.color must be one of "
                             "'always', 'never', 'auto' and not " + force_color)

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

    def pass_str(self, msg='PASS', move=MOVE_BACK):
        """
        Print a pass string (green colored).

        If the output does not support colors, just return the original string.
        """
        return move + self.PASS + msg + self.ENDC

    def skip_str(self, msg='SKIP', move=MOVE_BACK):
        """
        Print a skip string (yellow colored).

        If the output does not support colors, just return the original string.
        """
        return move + self.SKIP + msg + self.ENDC

    def fail_str(self, msg='FAIL', move=MOVE_BACK):
        """
        Print a fail string (red colored).

        If the output does not support colors, just return the original string.
        """
        return move + self.FAIL + msg + self.ENDC

    def error_str(self, msg='ERROR', move=MOVE_BACK):
        """
        Print a error string (red colored).

        If the output does not support colors, just return the original string.
        """
        return move + self.ERROR + msg + self.ENDC

    def interrupt_str(self, msg='INTERRUPT', move=MOVE_BACK):
        """
        Print an interrupt string (red colored).

        If the output does not support colors, just return the original string.
        """
        return move + self.INTERRUPT + msg + self.ENDC

    def warn_str(self, msg='WARN', move=MOVE_BACK):
        """
        Print an warning string (yellow colored).

        If the output does not support colors, just return the original string.
        """
        return move + self.WARN + msg + self.ENDC


#: Transparently handles colored terminal, when one is used
TERM_SUPPORT = TermSupport()


#: A collection of mapping from test statuses to colors to be used
#: consistently across the various plugins
TEST_STATUS_MAPPING = {'PASS': TERM_SUPPORT.PASS,
                       'ERROR': TERM_SUPPORT.ERROR,
                       'FAIL': TERM_SUPPORT.FAIL,
                       'SKIP': TERM_SUPPORT.SKIP,
                       'WARN': TERM_SUPPORT.WARN,
                       'INTERRUPTED': TERM_SUPPORT.INTERRUPT,
                       'CANCEL': TERM_SUPPORT.CANCEL}


#: A collection of mapping from test status to formatting functions
#: to be used consistently across the various plugins
TEST_STATUS_DECORATOR_MAPPING = {'PASS': TERM_SUPPORT.pass_str,
                                 'ERROR': TERM_SUPPORT.error_str,
                                 'FAIL': TERM_SUPPORT.fail_str,
                                 'SKIP': TERM_SUPPORT.skip_str,
                                 'WARN': TERM_SUPPORT.warn_str,
                                 'INTERRUPTED': TERM_SUPPORT.interrupt_str,
                                 'CANCEL': TERM_SUPPORT.skip_str}


class _StdOutputFile:

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

    def flush(self):
        """ File-object methods """

    @staticmethod
    def isatty():
        """ File-object methods """
        return False

    def seek(self):
        """ File-object methods """

    def tell(self):
        """ File-object methods """

    def getvalue(self):
        """
        Get all messages written to this "file"
        """
        return "\n".join((_[1] for _ in self._records
                          if _[0] == self._is_stdout))


class StdOutput:

    """
    Class to modify sys.stdout/sys.stderr
    """
    #: List of records of stored output when stdout/stderr is disabled
    records = []

    def __init__(self):
        self.stdout = self._stdout = sys.stdout
        self.stderr = self._stderr = sys.stderr
        self.__configured = False

    @staticmethod
    def _paginator_in_use():
        """
        :return: True when we output into paginator
        """
        return bool(isinstance(sys.stdout, Paginator))

    @property
    def configured(self):
        """
        Determines if a configuration of any sort has been performed
        """
        return self.__configured

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
        except IOError as detail:
            if not detail.errno == errno.EPIPE:
                raise

    def fake_outputs(self):
        """
        Replace sys.stdout/sys.stderr with in-memory-objects
        """
        sys.stdout = _StdOutputFile(True, self.records)
        sys.stderr = _StdOutputFile(False, self.records)
        self.__configured = True

    def enable_outputs(self):
        """
        Enable sys.stdout/sys.stderr (either with 2 streams or with paginator)
        """
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        self.__configured = True

    def enable_paginator(self):
        """
        Enable paginator
        """
        try:
            paginator = Paginator()
        except RuntimeError as details:
            # Paginator not available
            logging.getLogger('avocado.app.debug').error("Failed to enable "
                                                         "paginator: %s", details)
            return
        self.stdout = self.stderr = paginator
        self.__configured = True

    def enable_stderr(self):
        """
        Enable sys.stderr and disable sys.stdout
        """
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
        sys.stderr = self.stderr
        self.__configured = True

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


#: Allows modifying the sys.stdout/sys.stderr
STD_OUTPUT = StdOutput()


def early_start():
    """
    Replace all outputs with in-memory handlers
    """
    if os.environ.get('AVOCADO_LOG_DEBUG'):
        add_log_handler(LOG_UI.getChild("debug"), logging.StreamHandler,
                        sys.stdout, logging.DEBUG)
    if os.environ.get('AVOCADO_LOG_EARLY'):
        add_log_handler("avocado", logging.StreamHandler, sys.stdout, logging.DEBUG)
        add_log_handler(LOG_JOB, logging.StreamHandler, sys.stdout,
                        logging.DEBUG)
    else:
        STD_OUTPUT.fake_outputs()
        add_log_handler("avocado", MemStreamHandler, None, logging.DEBUG)
    logging.getLogger("avocado").level = logging.DEBUG


CONFIG = []


def del_last_configuration():
    if len(CONFIG) == 1:
        return
    configuration = CONFIG.pop()
    for logger_name in configuration:
        disable_log_handler(logger_name)
    configuration = CONFIG[-1]
    for logger_name, handlers in configuration.items():
        logger = logging.getLogger(logger_name)
        for handler in handlers:
            logger.addHandler(handler)


def reconfigure(args):
    """
    Adjust logging handlers accordingly to app args and re-log messages.
    """
    def save_handler(logger_name, handler, configuration):
        if logger_name not in configuration:
            configuration[logger_name] = []
        configuration[logger_name].append(handler)

    # Delete last configuration
    if len(CONFIG) != 0:
        last_configuration = CONFIG[-1]
        for logger_name in last_configuration:
            disable_log_handler(logger_name)

    configuration = {}
    # Reconfigure stream loggers
    enabled = args.get("core.show")
    if isinstance(enabled, list):
        enabled = set(enabled)
    if not isinstance(enabled, set):
        enabled = set(["app"])
        args["core.show"] = enabled
    if "none" in enabled:
        enabled = set([])
    elif "all" in enabled:
        enabled.update(BUILTIN_STREAMS)
    if os.environ.get("AVOCADO_LOG_EARLY"):
        enabled.add("early")
    if os.environ.get("AVOCADO_LOG_DEBUG"):
        enabled.add("debug")
    # TODO: Avocado relies on stdout/stderr on some places, re-log them here
    # for now. This should be removed once we replace them with logging.
    if enabled:
        if args.get('core.paginator') is True and TERM_SUPPORT.enabled:
            STD_OUTPUT.enable_paginator()
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
        save_handler(LOG_UI.name, app_handler, configuration)
    else:
        disable_log_handler(LOG_UI)
    app_err_handler = ProgressStreamHandler()
    app_err_handler.setFormatter(logging.Formatter("%(message)s"))
    app_err_handler.addFilter(FilterWarnAndMore())
    app_err_handler.stream = STD_OUTPUT.stderr
    LOG_UI.addHandler(app_err_handler)
    LOG_UI.propagate = False
    save_handler(LOG_UI.name, app_err_handler, configuration)
    if not os.environ.get("AVOCADO_LOG_EARLY"):
        LOG_JOB.getChild("stdout").propagate = False
        LOG_JOB.getChild("stderr").propagate = False
        if "early" in enabled:
            handler = add_log_handler("avocado", logging.StreamHandler,
                                      STD_OUTPUT.stdout, logging.DEBUG)
            save_handler("avocado", handler, configuration)
            handler = add_log_handler(LOG_JOB, logging.StreamHandler,
                                      STD_OUTPUT.stdout, logging.DEBUG)
            save_handler(LOG_JOB.name, handler, configuration)
        else:
            disable_log_handler("avocado")
    # Not enabled by env
    if not os.environ.get('AVOCADO_LOG_DEBUG'):
        if "debug" in enabled:
            handler = add_log_handler(LOG_UI.getChild("debug"),
                                      stream=STD_OUTPUT.stdout)
            save_handler(LOG_UI.getChild("debug").name, handler, configuration)
        else:
            disable_log_handler(LOG_UI.getChild("debug"))

    # Add custom loggers
    for name in [_ for _ in enabled if _ not in BUILTIN_STREAMS]:
        stream_level = re.split(r'(?<!\\):', name, maxsplit=1)
        name = stream_level[0]
        if len(stream_level) == 1:
            level = logging.DEBUG
        else:
            level = (int(stream_level[1]) if stream_level[1].isdigit()
                     else logging.getLevelName(stream_level[1].upper()))
        try:
            handler = add_log_handler(name, logging.StreamHandler,
                                      STD_OUTPUT.stdout, level)
            save_handler(name, handler, configuration)
        except ValueError as details:
            LOG_UI.error("Failed to set logger for --show %s:%s: %s.",
                         name, level, details)
            sys.exit(exit_codes.AVOCADO_FAIL)
    # Remove the in-memory handlers
    for handler in logging.getLogger('avocado').handlers:
        if isinstance(handler, MemStreamHandler):
            logging.getLogger('avocado').handlers.remove(handler)

    # Log early_messages
    for record in MemStreamHandler.log:
        logging.getLogger(record.name).handle(record)

    CONFIG.append(configuration)


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
        except (KeyboardInterrupt, SystemExit):  # pylint: disable=W0706
            raise
        except Exception:  # pylint: disable=W0703
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


class Paginator:

    """
    Paginator that uses less to display contents on the terminal.

    Contains cleanup handling for when user presses 'q' (to quit less).
    """

    def __init__(self):
        self.pipe = None
        paginator = os.environ.get('PAGER')
        if not paginator:
            try:
                paginator = f"{utils_path.find_command('less')} -FRX"
            except utils_path.CmdNotFoundError as details:
                raise RuntimeError(f"Unable to enable pagination: {details}")

        self.pipe = os.popen(paginator, 'w')

    def __del__(self):
        self.close()

    def close(self):
        if self.pipe:
            try:
                self.pipe.close()
            except OSError:
                pass

    def write(self, msg):
        if self.pipe:
            try:
                self.pipe.write(msg)
            except (OSError, ValueError):
                pass

    def flush(self):
        if self.pipe and not self.pipe.closed:
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
    if isinstance(logger, str):
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
    if not logger:
        return
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    # Handlers might be reused elsewhere, can't delete them
    while logger.handlers:
        logger.handlers.pop()
    logger.handlers.append(logging.NullHandler())
    logger.propagate = False


class LoggingFile:

    """
    File-like object that will receive messages pass them to logging.
    """

    def __init__(self, prefixes=None, level=logging.DEBUG,
                 loggers=None):
        """
        Constructor. Sets prefixes and which loggers are going to be used.

        :param prefixes: Prefix per logger to be prefixed to each line.
        :param level: Log level to be used when writing messages.
        :param loggers: Loggers into which write should be issued. (list)
        """
        if not loggers:
            loggers = [logging.getLogger()]
        self._level = level
        self._loggers = loggers
        if prefixes is None:
            prefixes = [""] * len(loggers)
        self._prefixes = prefixes

    def write(self, data):
        """"
        Splits the line to individual lines and forwards them into loggers
        with expected prefixes. It includes the tailing newline <lf> as well
        as the last partial message. Do configure your logging to not to add
        newline <lf> automatically.
        :param data - Raw data (a string) that will be processed.
        """
        # splitlines() discards a trailing blank line, so use split() instead
        data_lines = data.split('\n')
        if len(data_lines) > 1:     # when not last line, contains \n
            self._log_line(f"{data_lines[0]}\n")
        for line in data_lines[1:-1]:
            self._log_line(f"{line}\n")
        if data_lines[-1]:  # Last line does not contain \n
            self._log_line(data_lines[-1])

    def _log_line(self, line):
        """
        Forwards line to all the expected loggers along with expected prefix
        """
        for logger, prefix in zip(self._loggers, self._prefixes):
            logger.log(self._level, prefix + line)

    def flush(self):
        pass

    @staticmethod
    def isatty():
        return False

    def add_logger(self, logger, prefix=""):
        self._loggers.append(logger)
        self._prefixes.append(prefix)

    def rm_logger(self, logger):
        idx = self._loggers.index(logger)
        self._loggers.remove(logger)
        self._prefixes = self._prefixes[:idx] + self._prefixes[idx+1:]


class Throbber:

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
    msg_fmt = 'Failed to load plugin from module "%s": %s :\n%s'
    config = settings.as_dict()
    silenced = config.get('plugins.skip_broken_plugin_notification')
    for failure in failures:
        if failure[0].module_name in silenced:
            continue
        if hasattr(failure[1], "__traceback__"):
            str_tb = ''.join(traceback.format_tb(failure[1].__traceback__))
        else:
            str_tb = "Traceback not available"
        LOG_UI.error(msg_fmt, failure[0].module_name,
                     failure[1].__repr__(), str_tb)
