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
# client/shared/test.py
# Authors: Martin J Bligh <mbligh@google.com>,
#          Andy Whitcroft <apw@shadowen.org>

"""
Contains the base test implementation, used as a base for the actual
framework tests.
"""

import inspect
import logging
import os
import pipes
import re
import shutil
import sys
import tempfile
import time
import unittest

from difflib import unified_diff
from six import string_types, iteritems

from . import data_dir
from . import defaults
from . import exceptions
from . import output
from . import parameters
from . import sysinfo
from ..utils import asset
from ..utils import astring
from ..utils import data_structures
from ..utils import genio
from ..utils import path as utils_path
from ..utils import process
from ..utils import stacktrace
from .decorators import skip
from .settings import settings
from .version import VERSION
from .output import LOG_JOB


#: Environment variable used to store the location of a temporary
#: directory which is preserved across all tests execution (usually in
#: one job)
COMMON_TMPDIR_NAME = 'AVOCADO_TESTS_COMMON_TMPDIR'

#: The list of test attributes that are used as the test state, which
#: is given to the test runner via the queue they share
TEST_STATE_ATTRIBUTES = ('name', 'logdir', 'logfile',
                         'status', 'running', 'paused',
                         'time_start', 'time_elapsed', 'time_end',
                         'fail_reason', 'fail_class', 'traceback',
                         'timeout', 'whiteboard')


class RawFileHandler(logging.FileHandler):

    """
    File Handler that doesn't include arbitrary characters to the
    logged stream but still respects the formatter.
    """

    def emit(self, record):
        """
        Modifying the original emit() to avoid including a new line
        in streams that should be logged in its purest form, like in
        stdout/stderr recordings.
        """
        if self.stream is None:
            self.stream = self._open()
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(astring.to_text(msg, self.encoding,
                                         'xmlcharrefreplace'))
            self.flush()
        except Exception:
            self.handleError(record)


class TestID(object):

    """
    Test ID construction and representation according to specification

    This class wraps the representation of both Avocado's Test ID
    specification and Avocado's Test Name, which is part of a Test ID.
    """

    def __init__(self, uid, name, variant=None, no_digits=None):
        """
        Constructs a TestID instance

        :param uid: unique test id (within the job)
        :param name: test name, as returned by the Avocado test resolver
                     (AKA as test loader)
        :param variant: the variant applied to this Test ID
        :type variant: dict
        :param no_digits: number of digits of the test uid
        """
        self.uid = uid
        if no_digits is not None and no_digits >= 0:
            self.str_uid = str(uid).zfill(no_digits if no_digits else 3)
        else:
            self.str_uid = str(uid)
        self.name = name or "<unknown>"
        if variant is None or variant["variant_id"] is None:
            self.variant = None
            self.str_variant = ""
        else:
            self.variant = variant["variant_id"]
            self.str_variant = ";%s" % self.variant

    def __str__(self):
        return "%s-%s%s" % (self.str_uid, self.name, self.str_variant)

    def __repr__(self):
        return repr(str(self))

    def __eq__(self, other):
        if isinstance(other, string_types):
            return str(self) == other
        else:
            return self.__dict__ == other.__dict__

    @property
    def str_filesystem(self):
        """
        Test ID in a format suitable for use in file systems

        The string returned should be safe to be used as a file or
        directory name.  This file system version of the test ID may
        have to shorten either the Test Name or the Variant ID.

        The first component of a Test ID, the numeric unique test id,
        AKA "uid", will be used as a an stable identifier between the
        Test ID and the file or directory created based on the return
        value of this method.  If the filesystem can not even
        represent the "uid", than an exception will be raised.

        For Test ID "001-mytest;foo", examples of shortened file
        system versions include "001-mytest;f" or "001-myte;foo".

        :raises: RuntimeError if the test ID cannot be converted to a
                 filesystem representation.
        """
        test_id = str(self)
        test_id_fs = astring.string_to_safe_path(test_id)
        if len(test_id) == len(test_id_fs):    # everything fits in
            return test_id_fs
        idx_fit_variant = len(test_id_fs) - len(self.str_variant)
        if idx_fit_variant > len(self.str_uid):     # full uid+variant
            return (test_id_fs[:idx_fit_variant] +
                    astring.string_to_safe_path(self.str_variant))
        elif len(self.str_uid) <= len(test_id_fs):   # full uid
            return astring.string_to_safe_path(self.str_uid + self.str_variant)
        else:       # not even uid could be stored in fs
            raise RuntimeError('Test ID is too long to be stored on the '
                               'filesystem: "%s"\nFull Test ID: "%s"'
                               % (self.str_uid, str(self)))


class TestData(object):

    """
    Class that adds the ability for tests to have access to data files

    Writers of new test types can change the completely change the behavior
    and still be compatible by providing an :attr:`DATA_SOURCES` attribute
    and a meth:`get_data` method.
    """

    #: Defines the name of data sources that this implementation makes
    #: available.  Users may choose to pick data file from a specific
    #: source.
    DATA_SOURCES = ["variant", "test", "file"]

    def __init__(self):
        # Maximal allowed file name length is 255
        file_datadir = None
        if (self.filename is not None and
                len(os.path.basename(self.filename)) < 251):
            file_datadir = self.filename + '.data'
        self._data_sources_mapping = {
            "variant": [lambda: file_datadir,
                        lambda: "%s.%s" % (self.__class__.__name__,
                                           self._testMethodName),
                        lambda: self.name.variant],
            "test": [lambda: file_datadir,
                     lambda: "%s.%s" % (self.__class__.__name__,
                                        self._testMethodName)],
            "file": [lambda: file_datadir]
        }

    def _check_valid_data_source(self, source):
        """
        Utility to check if user chose a specific data source

        :param source: either None for no specific selection or a source name
        :type source: None or str
        :raises: ValueError
        """
        if source is not None and source not in self.DATA_SOURCES:
            msg = 'Data file source requested (%s) is not one of: %s'
            msg %= (source, ', '.join(self.DATA_SOURCES))
            raise ValueError(msg)

    def _get_datadir(self, source):
        path_components = self._data_sources_mapping.get(source)
        if path_components is None:
            return

        # evaluate lazily, needed when the class changes its own
        # information such as its datadir
        path_components = [func() for func in path_components]
        if None in path_components:
            return

        # if path components are absolute paths, let's believe that
        # they have already been treated (such as the entries that
        # return the self.datadir).  If not, let's split the path
        # components so that they can be treated in the next loop
        split_path_components = []
        for path_component in path_components:
            if not os.path.isabs(path_component):
                split_path_components += path_component.split(os.path.sep)
            else:
                split_path_components.append(path_component)

        # now, make sure each individual path component can be represented
        # in the filesystem.  again, if it's an absolute path, do nothing
        paths = []
        for path in split_path_components:
            if os.path.isabs(path):
                paths.append(path)
            else:
                paths.append(astring.string_to_safe_path(path))

        return os.path.join(*paths)

    def get_data(self, filename, source=None, must_exist=True):
        """
        Retrieves the path to a given data file.

        This implementation looks for data file in one of the sources
        defined by the :attr:`DATA_SOURCES` attribute.

        :param filename: the name of the data file to be retrieved
        :type filename: str
        :param source: one of the defined data sources.  If not set,
                       all of the :attr:`DATA_SOURCES` will be attempted
                       in the order they are defined
        :type source: str
        :param must_exist: whether the existence of a file is checked for
        :type must_exist: bool
        :rtype: str or None
        """
        log_fmt = 'DATA (filename=%s) => %s (%s)'
        if source is None:
            sources = self.DATA_SOURCES
        else:
            self._check_valid_data_source(source)
            sources = [source]
        for attempt_source in sources:
            datadir = self._get_datadir(attempt_source)
            if datadir is not None:
                # avoid returning a slash after the data directory name
                # when a file was not requested (thus return the data
                # directory itself)
                if not filename:
                    path = datadir
                else:
                    path = os.path.join(datadir, filename)
                if not must_exist:
                    self.log.debug(log_fmt, filename, path,
                                   ("assumed to be located at %s source "
                                    "dir" % attempt_source))
                    return path
                else:
                    if os.path.exists(path):
                        self.log.debug(log_fmt, filename, path,
                                       "found at %s source dir" % attempt_source)
                        return path

        self.log.debug(log_fmt, filename, "NOT FOUND",
                       "data sources: %s" % ', '.join(sources))


class Test(unittest.TestCase, TestData):

    """
    Base implementation for the test class.

    You'll inherit from this to write your own tests. Typically you'll want
    to implement setUp(), test*() and tearDown() methods on your own tests.
    """
    #: Arbitrary string which will be stored in `$logdir/whiteboard` location
    #: when the test finishes.
    whiteboard = ''
    #: (unix) time when the test started (could be forced from test)
    time_start = -1
    #: (unix) time when the test finished (could be forced from test)
    time_end = -1
    #: duration of the test execution (always recalculated from time_end -
    #: time_start
    time_elapsed = -1
    #: Test timeout (the timeout from params takes precedence)
    timeout = None

    def __init__(self, methodName='test', name=None, params=None,
                 base_logdir=None, job=None, runner_queue=None, tags=None):
        """
        Initializes the test.

        :param methodName: Name of the main method to run. For the sake of
                           compatibility with the original unittest class,
                           you should not set this.
        :param name: Pretty name of the test name. For normal tests,
                     written with the avocado API, this should not be
                     set.  This is reserved for internal Avocado use,
                     such as when running random executables as tests.
        :type name: :class:`avocado.core.test.TestID`
        :param base_logdir: Directory where test logs should go. If None
                            provided, it'll use
                            :func:`avocado.data_dir.create_job_logs_dir`.
        :param job: The job that this test is part of.
        """
        def record_and_warn(*args, **kwargs):
            """ Record call to this function and log warning """
            if not self.__log_warn_used:
                self.__log_warn_used = True
            return original_log_warn(*args, **kwargs)

        if name is not None:
            self.__name = name
        else:
            self.__name = TestID(0, self.__class__.__name__)

        self.__job = job
        self.__tags = tags

        if base_logdir is None:
            base_logdir = data_dir.create_job_logs_dir()
        base_logdir = os.path.join(base_logdir, 'test-results')
        logdir = os.path.join(base_logdir, self.name.str_filesystem)
        if os.path.exists(logdir):
            raise exceptions.TestSetupFail("Log dir already exists, this "
                                           "should never happen: %s"
                                           % logdir)
        self.__logdir = utils_path.init_dir(logdir)

        # Replace '/' with '_' to avoid splitting name into multiple dirs
        genio.set_log_file_dir(self.logdir)
        self.__logfile = os.path.join(self.logdir, 'debug.log')
        self._ssh_logfile = os.path.join(self.logdir, 'remote.log')

        self._stdout_file = os.path.join(self.logdir, 'stdout')
        self._stderr_file = os.path.join(self.logdir, 'stderr')
        self._output_file = os.path.join(self.logdir, 'output')
        self._logging_handlers = {}

        self.__outputdir = utils_path.init_dir(self.logdir, 'data')
        self.__sysinfo_enabled = getattr(self.job, 'sysinfo', False)
        if self.__sysinfo_enabled:
            self.__sysinfodir = utils_path.init_dir(self.logdir, 'sysinfo')
            self.__sysinfo_logger = sysinfo.SysInfo(basedir=self.__sysinfodir)

        self.__log = LOG_JOB
        original_log_warn = self.log.warning
        self.__log_warn_used = False
        self.log.warn = self.log.warning = record_and_warn

        self.log.info('INIT %s', self.name)

        paths = ['/test/*']
        if params is None:
            params = []
        elif isinstance(params, tuple):
            params, paths = params[0], params[1]
        self.__params = parameters.AvocadoParams(params, paths,
                                                 self.__log.name)
        default_timeout = getattr(self, "timeout", None)
        self.timeout = self.params.get("timeout", default=default_timeout)

        self.__status = None
        self.__fail_reason = None
        self.__fail_class = None
        self.__traceback = None
        self.__cache_dirs = None    # Is initialized lazily

        self.__running = False
        self.paused = False
        self.paused_msg = ''

        self.__runner_queue = runner_queue

        base_tmpdir = getattr(job, "tmpdir", None)
        # When tmpdir not specified by job, use logdir to preserve all data
        if base_tmpdir is None:
            base_tmpdir = tempfile.mkdtemp(prefix="tmp_dir", dir=self.logdir)
        self.__workdir = os.path.join(base_tmpdir,
                                      self.name.str_filesystem)
        utils_path.init_dir(self.__workdir)

        self.log.debug("Test metadata:")
        if self.filename:
            self.log.debug("  filename: %s", self.filename)
        try:
            teststmpdir = self.teststmpdir
        except EnvironmentError:
            pass
        else:
            self.log.debug("  teststmpdir: %s", teststmpdir)
        self.log.debug("  workdir: %s", self.workdir)

        unittest.TestCase.__init__(self, methodName=methodName)
        TestData.__init__(self)

    @property
    def name(self):
        """
        Returns the Test ID, which includes the test name

        :rtype: TestID
        """
        return self.__name

    @property
    def job(self):
        """
        The job this test is associated with
        """
        return self.__job

    @property
    def tags(self):
        """
        The tags associated with this test
        """
        return self.__tags

    @property
    def log(self):
        """
        The enhanced test log
        """
        return self.__log

    @property
    def logdir(self):
        """
        Path to this test's logging dir
        """
        return self.__logdir

    @property
    def logfile(self):
        """
        Path to this test's main `debug.log` file
        """
        return self.__logfile

    @property
    def outputdir(self):
        """
        Directory available to test writers to attach files to the results
        """
        return self.__outputdir

    @property
    def params(self):
        """
        Parameters of this test (AvocadoParam instance)
        """
        return self.__params

    @property
    def basedir(self):
        """
        The directory where this test (when backed by a file) is located at
        """
        if self.filename is not None:
            return os.path.dirname(self.filename)
        else:
            return None

    @property
    def filename(self):
        """
        Returns the name of the file (path) that holds the current test
        """
        try:
            possibly_compiled = inspect.getfile(self.__class__)
            if possibly_compiled.endswith('.pyc') or possibly_compiled.endswith('.pyo'):
                source = possibly_compiled[:-1]
            else:
                source = possibly_compiled
        except TypeError:
            return None

        if os.path.exists(source):
            return source
        else:
            return None

    @property
    def teststmpdir(self):
        """
        Returns the path of the temporary directory that will stay the
        same for all tests in a given Job.
        """
        env_var = COMMON_TMPDIR_NAME
        path = os.environ.get(env_var)
        if path is None:
            msg = 'Environment Variable %s is not set.' % env_var
            raise EnvironmentError(msg)
        return path

    @property
    def workdir(self):
        """
        This property returns a writable directory that exists during
        the entire test execution, but will be cleaned up once the
        test finishes.

        It can be used on tasks such as decompressing source tarballs,
        building software, etc.
        """
        return self.__workdir

    @property
    def cache_dirs(self):
        """
        Returns a list of cache directories as set in config file.
        """
        if self.__cache_dirs is None:
            self.__cache_dirs = data_dir.get_cache_dirs()
        return self.__cache_dirs

    @property
    def runner_queue(self):
        """
        The communication channel between test and test runner
        """
        return self.__runner_queue

    def set_runner_queue(self, runner_queue):
        """
        Override the runner_queue
        """
        if self.__runner_queue is not None:
            raise RuntimeError("Overriding of runner_queue multiple "
                               "times is not allowed -> old=%s new=%s"
                               % (self.__runner_queue, runner_queue))
        self.__runner_queue = runner_queue

    @property
    def status(self):
        """
        The result status of this test
        """
        return self.__status

    @property
    def running(self):
        """
        Whether this test is currently being executed
        """
        return self.__running

    @property
    def fail_reason(self):
        return self.__fail_reason

    @property
    def fail_class(self):
        return self.__fail_class

    @property
    def traceback(self):
        return self.__traceback

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return "Test(%r)" % self.name

    def _tag_start(self):
        self.log.info('START %s', self.name)
        self.__running = True
        self.time_start = time.time()

    def _tag_end(self):
        self.__running = False
        self.time_end = time.time()
        # for consistency sake, always use the same stupid method
        self._update_time_elapsed(self.time_end)

    def _update_time_elapsed(self, current_time=None):
        if current_time is None:
            current_time = time.time()
        self.time_elapsed = current_time - self.time_start

    def report_state(self):
        """
        Send the current test state to the test runner process
        """
        if self.runner_queue is not None:
            self.runner_queue.put(self.get_state())

    def get_state(self):
        """
        Serialize selected attributes representing the test state

        :returns: a dictionary containing relevant test state data
        :rtype: dict
        """
        if self.running and self.time_start:
            self._update_time_elapsed()
        state = {key: getattr(self, key, None) for (key) in TEST_STATE_ATTRIBUTES}
        state['class_name'] = self.__class__.__name__
        state['job_logdir'] = self.job.logdir
        state['job_unique_id'] = self.job.unique_id
        try:
            state['params'] = [(path, key, value)
                               for path, key, value
                               in self.__params.iteritems()]
        except Exception:
            state['params'] = None
        return state

    def _register_log_file_handler(self, logger, formatter, filename,
                                   log_level=logging.DEBUG, raw=False):
        if raw:
            file_handler = RawFileHandler(filename=filename,
                                          encoding=astring.ENCODING)
        else:
            file_handler = logging.FileHandler(filename=filename)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        self._logging_handlers[logger.name] = file_handler

    def _start_logging(self):
        """
        Simple helper for adding a file logger to the root logger.
        """
        self.file_handler = logging.FileHandler(filename=self.logfile)
        self.file_handler.setLevel(logging.DEBUG)

        fmt = '%(asctime)s %(levelname)-5.5s| %(message)s'
        formatter = logging.Formatter(fmt=fmt, datefmt='%H:%M:%S')

        self.file_handler.setFormatter(formatter)
        self.log.addHandler(self.file_handler)

        stream_fmt = '%(message)s'
        stream_formatter = logging.Formatter(fmt=stream_fmt)

        log_test_stdout = LOG_JOB.getChild("stdout")
        log_test_stderr = LOG_JOB.getChild("stderr")
        log_test_output = LOG_JOB.getChild("output")

        self._register_log_file_handler(log_test_stdout,
                                        stream_formatter,
                                        self._stdout_file,
                                        raw=True)
        self._register_log_file_handler(log_test_stderr,
                                        stream_formatter,
                                        self._stderr_file,
                                        raw=True)
        self._register_log_file_handler(log_test_output,
                                        stream_formatter,
                                        self._output_file,
                                        raw=True)

        self._register_log_file_handler(logging.getLogger('paramiko'),
                                        formatter,
                                        self._ssh_logfile)

        if isinstance(sys.stdout, output.LoggingFile):
            sys.stdout.add_logger(log_test_stdout)
        if isinstance(sys.stderr, output.LoggingFile):
            sys.stderr.add_logger(log_test_stderr)

    def _stop_logging(self):
        """
        Stop the logging activity of the test by cleaning the logger handlers.
        """
        self.log.removeHandler(self.file_handler)
        if isinstance(sys.stderr, output.LoggingFile):
            sys.stderr.rm_logger(LOG_JOB.getChild("stderr"))
        if isinstance(sys.stdout, output.LoggingFile):
            sys.stdout.rm_logger(LOG_JOB.getChild("stdout"))
        for name, handler in iteritems(self._logging_handlers):
            logging.getLogger(name).removeHandler(handler)

    def _record_reference(self, produced_file_path, reference_file_name):
        '''
        Saves a copy of a file produced by the test into a reference file

        This utility method will copy the produced file into the expected
        reference file location, which can later be used for comparison
        on subsequent test runs.

        Note: A reference file is a "golden" file with content that is
        expected to match what was produced during the test.  If the
        produced content matches the reference file content, the test
        performed correctly.

        :param produced_file_path: the location of the file that was produced
                                   by this test execution
        :type produced_file_path: str
        :param reference_file_name: the name of the file that will be used on
                                    subsequent runs to check the test produced
                                    the correct content.  This file will be
                                    saved into a location obtained by
                                    calling :meth:`get_data()`.
        :type reference_file_name: str
        '''
        reference_path = self.get_data(reference_file_name, must_exist=False)
        if reference_path is not None:
            utils_path.init_dir(os.path.dirname(reference_path))
            shutil.copyfile(produced_file_path, reference_path)

    def _check_reference(self, produced_file_path, reference_file_name,
                         diff_file_name, child_log_name, name='Content'):
        '''
        Compares the file produced by the test with the reference file

        :param produced_file_path: the location of the file that was produced
                                   by this test execution
        :type produced_file_path: str
        :param reference_file_name: the name of the file that will compared
                                    with the content produced by this test
        :type reference_file_name: str
        :param diff_file_name: in case of differences between the produced
                               and reference file, a file with this name will
                               be saved to the test results directory, with
                               the differences in unified diff format
        :type diff_file_name: str
        :param child_log_name: the name of a logger, child of :data:`LOG_JOB`,
                               to be used when logging the content differences
        :type child_log_name: str
        :param name: optional parameter for a descriptive name of the type of
                     content being checked here
        :type name: str
        :returns: True if the check was performed (there was a reference file) and
                  was successful, and False otherwise (there was no such reference
                  file and thus no check was performed).
        :raises: :class:`exceptions.TestFail` when the check is performed and fails
        '''
        reference_path = self.get_data(reference_file_name)
        if reference_path is not None:
            expected = genio.read_file(reference_path)
            actual = genio.read_file(produced_file_path)
            diff_path = os.path.join(self.logdir, diff_file_name)

            fmt = '%(message)s'
            formatter = logging.Formatter(fmt=fmt)
            log_diff = LOG_JOB.getChild(child_log_name)
            self._register_log_file_handler(log_diff,
                                            formatter,
                                            diff_path)

            diff = unified_diff(expected.splitlines(), actual.splitlines(),
                                fromfile=reference_path,
                                tofile=produced_file_path)
            diff_content = []
            for diff_line in diff:
                diff_content.append(diff_line.rstrip('\n'))

            if diff_content:
                self.log.debug('%s Diff:', name)
                for line in diff_content:
                    log_diff.debug(line)
                self.fail('Actual test %s differs from expected one' % name)
            else:
                return True
        return False

    def _run_avocado(self):
        """
        Auxiliary method to run_avocado.
        """
        # If the test contains an output.expected file, it requires
        # changing the mode of operation of the process.* utility
        # methods, so that after the test finishes, the output
        # produced can be compared to the expected one.  This runs in
        # its own process, so the change should not effect other
        # components using process.* functions.
        if self.get_data('output.expected') is not None:
            process.OUTPUT_CHECK_RECORD_MODE = 'combined'

        testMethod = getattr(self, self._testMethodName)
        self._start_logging()
        if self.__sysinfo_enabled:
            self.__sysinfo_logger.start_test_hook()
        test_exception = None
        cleanup_exception = None
        output_check_exception = None
        stdout_check_exception = None
        stderr_check_exception = None
        skip_test = getattr(testMethod, '__skip_test_decorator__', False)
        try:
            if skip_test is False:
                self.setUp()
        except exceptions.TestSkipError as details:
            skip_test = True
            stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
            raise exceptions.TestSkipError(details)
        except exceptions.TestCancel as details:
            stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
            raise
        except:  # Old-style exceptions are not inherited from Exception()
            stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
            details = sys.exc_info()[1]
            raise exceptions.TestSetupFail(details)
        else:
            try:
                testMethod()
            except exceptions.TestCancel as details:
                stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
                raise
            except:  # Old-style exceptions are not inherited from Exception() pylint: disable=W0702
                stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
                details = sys.exc_info()[1]
                if not isinstance(details, Exception):  # Avoid passing nasty exc
                    details = exceptions.TestError("%r: %s" % (details, details))
                test_exception = details
                self.log.debug("Local variables:")
                local_vars = inspect.trace()[1][0].f_locals
                for key, value in iteritems(local_vars):
                    self.log.debug(' -> %s %s: %s', key, type(value), value)
        finally:
            try:
                if skip_test is False:
                    self.tearDown()
            except exceptions.TestSkipError as details:
                stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
                skip_illegal_msg = ('Using skip decorators in tearDown() '
                                    'is not allowed in '
                                    'avocado, you must fix your '
                                    'test. Original skip exception: %s' %
                                    details)
                raise exceptions.TestError(skip_illegal_msg)
            except exceptions.TestCancel as details:
                stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
                raise
            except:  # avoid old-style exception failures pylint: disable=W0702
                stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
                details = sys.exc_info()[1]
                cleanup_exception = exceptions.TestSetupFail(details)

        whiteboard_file = os.path.join(self.logdir, 'whiteboard')
        genio.write_file(whiteboard_file, self.whiteboard)

        if self.job is not None:
            job_standalone = getattr(self.job.args, 'standalone', False)
            output_check_record = getattr(self.job.args,
                                          'output_check_record', 'none')
            output_check = getattr(self.job.args, 'output_check', 'on')

            # record the output if the modes are valid
            if output_check_record == 'combined':
                self._record_reference(self._output_file,
                                       "output.expected")
            else:
                if output_check_record in ['all', 'both', 'stdout']:
                    self._record_reference(self._stdout_file,
                                           "stdout.expected")
                if output_check_record in ['all', 'both', 'stderr']:
                    self._record_reference(self._stderr_file,
                                           "stderr.expected")

            # check the output and produce test failures
            if ((not job_standalone or
                 output_check_record != 'none') and output_check == 'on'):
                output_checked = False
                try:
                    output_checked = self._check_reference(
                        self._output_file,
                        'output.expected',
                        'output.diff',
                        'output_diff',
                        'Output')
                except Exception as details:
                    stacktrace.log_exc_info(sys.exc_info(),
                                            logger=LOG_JOB)
                    output_check_exception = details
                if not output_checked:
                    try:
                        self._check_reference(self._stdout_file,
                                              'stdout.expected',
                                              'stdout.diff',
                                              'stdout_diff',
                                              'Stdout')
                    except Exception as details:
                        # output check was performed (and failed)
                        output_checked = True
                        stacktrace.log_exc_info(sys.exc_info(),
                                                logger=LOG_JOB)
                        stdout_check_exception = details
                    try:
                        self._check_reference(self._stderr_file,
                                              'stderr.expected',
                                              'stderr.diff',
                                              'stderr_diff',
                                              'Stderr')
                    except Exception as details:
                        stacktrace.log_exc_info(sys.exc_info(),
                                                logger=LOG_JOB)
                        stderr_check_exception = details

        if self.__sysinfo_enabled:
            self.__sysinfo_logger.end_test_hook()

        # pylint: disable=E0702
        if test_exception is not None:
            raise test_exception
        elif cleanup_exception is not None:
            raise cleanup_exception
        elif output_check_exception is not None:
            raise output_check_exception
        elif stdout_check_exception is not None:
            raise stdout_check_exception
        elif stderr_check_exception is not None:
            raise stderr_check_exception
        elif self.__log_warn_used:
            raise exceptions.TestWarn("Test passed but there were warnings "
                                      "during execution. Check the log for "
                                      "details.")

        self.__status = 'PASS'

    def _setup_environment_variables(self):
        os.environ['AVOCADO_VERSION'] = VERSION
        if self.basedir is not None:
            os.environ['AVOCADO_TEST_BASEDIR'] = self.basedir
        os.environ['AVOCADO_TEST_WORKDIR'] = self.workdir
        os.environ['AVOCADO_TEST_LOGDIR'] = self.logdir
        os.environ['AVOCADO_TEST_LOGFILE'] = self.logfile
        os.environ['AVOCADO_TEST_OUTPUTDIR'] = self.outputdir
        if self.__sysinfo_enabled:
            os.environ['AVOCADO_TEST_SYSINFODIR'] = self.__sysinfodir

    def run_avocado(self):
        """
        Wraps the run method, for execution inside the avocado runner.

        :result: Unused param, compatibility with :class:`unittest.TestCase`.
        """
        self._setup_environment_variables()
        try:
            self._tag_start()
            self._run_avocado()
        except exceptions.TestBaseException as detail:
            self.__status = detail.status
            self.__fail_class = detail.__class__.__name__
            self.__fail_reason = astring.to_text(detail)
            self.__traceback = stacktrace.prepare_exc_info(sys.exc_info())
        except AssertionError as detail:
            self.__status = 'FAIL'
            self.__fail_class = detail.__class__.__name__
            self.__fail_reason = astring.to_text(detail)
            self.__traceback = stacktrace.prepare_exc_info(sys.exc_info())
        except Exception as detail:
            self.__status = 'ERROR'
            tb_info = stacktrace.tb_info(sys.exc_info())
            self.__traceback = stacktrace.prepare_exc_info(sys.exc_info())
            try:
                self.__fail_class = astring.to_text(detail.__class__.__name__)
                self.__fail_reason = astring.to_text(detail)
            except TypeError:
                self.__fail_class = "Exception"
                self.__fail_reason = ("Unable to get exception, check the "
                                      "traceback for details.")
            for e_line in tb_info:
                self.log.error(e_line)
        finally:
            self._tag_end()
            self._report()
            self.log.info("")
            self._stop_logging()

    def _report(self):
        """
        Report result to the logging system.
        """
        if self.fail_reason is not None:
            self.log.error("%s %s -> %s: %s", self.status,
                           self.name,
                           self.fail_class,
                           self.fail_reason)

        else:
            if self.status is None:
                self.__status = 'INTERRUPTED'
            self.log.info("%s %s", self.status,
                          self.name)

    def fail(self, message=None):
        """
        Fails the currently running test.

        After calling this method a test will be terminated and have its status
        as FAIL.

        :param message: an optional message that will be recorded in the logs
        :type message: str
        """
        raise exceptions.TestFail(message)

    def error(self, message=None):
        """
        Errors the currently running test.

        After calling this method a test will be terminated and have its status
        as ERROR.

        :param message: an optional message that will be recorded in the logs
        :type message: str
        """
        raise exceptions.TestError(message)

    def cancel(self, message=None):
        """
        Cancels the test.

        This method is expected to be called from the test method, not
        anywhere else, since by definition, we can only cancel a test that
        is currently under execution. If you call this method outside the
        test method, avocado will mark your test status as ERROR, and
        instruct you to fix your test in the error message.

        :param message: an optional message that will be recorded in the logs
        :type message: str
        """
        raise exceptions.TestCancel(message)

    def fetch_asset(self, name, asset_hash=None, algorithm=None,
                    locations=None, expire=None):
        """
        Method o call the utils.asset in order to fetch and asset file
        supporting hash check, caching and multiple locations.

        :param name: the asset filename or URL
        :param asset_hash: asset hash (optional)
        :param algorithm: hash algorithm (optional, defaults to
                          :data:`avocado.utils.asset.DEFAULT_HASH_ALGORITHM`)
        :param locations: list of URLs from where the asset can be
                          fetched (optional)
        :param expire: time for the asset to expire
        :raise EnvironmentError: When it fails to fetch the asset
        :returns: asset file local path
        """
        if expire is not None:
            expire = data_structures.time_to_seconds(str(expire))
        return asset.Asset(name, asset_hash, algorithm, locations,
                           self.cache_dirs, expire).fetch()


class SimpleTest(Test):

    """
    Run an arbitrary command that returns either 0 (PASS) or !=0 (FAIL).
    """

    DATA_SOURCES = ["variant", "file"]

    def __init__(self, name, params=None, base_logdir=None, job=None,
                 executable=None):
        if executable is None:
            executable = name.name
        self._filename = executable
        super(SimpleTest, self).__init__(name=name, params=params,
                                         base_logdir=base_logdir, job=job)
        # Maximal allowed file name length is 255
        file_datadir = None
        if (self.filename is not None and
                len(os.path.basename(self.filename)) < 251):
            file_datadir = self.filename + '.data'
        self._data_sources_mapping = {"variant": [lambda: file_datadir,
                                                  lambda: self.name.variant],
                                      "file": [lambda: file_datadir]}
        self._command = None
        if self.filename is not None:
            self._command = pipes.quote(self.filename)
            # process.run expects unicode as the command, but pipes.quote
            # turns it into a "bytes" array in Python 2
            if not astring.is_text(self._command):
                self._command = astring.to_text(self._command, defaults.ENCODING)

    @property
    def filename(self):
        """
        Returns the name of the file (path) that holds the current test
        """
        return os.path.abspath(self._filename)

    def _log_detailed_cmd_info(self, result):
        """
        Log detailed command information.

        :param result: :class:`avocado.utils.process.CmdResult` instance.
        """
        self.log.info("Exit status: %s", result.exit_status)
        self.log.info("Duration: %s", result.duration)

    def _execute_cmd(self):
        """
        Run the executable, and log its detailed execution.
        """
        try:
            test_params = dict([(str(key), str(val)) for _, key, val in
                                self.params.iteritems()])

            result = process.run(self._command, verbose=True,
                                 env=test_params, encoding=defaults.ENCODING)

            self._log_detailed_cmd_info(result)
        except process.CmdError as details:
            self._log_detailed_cmd_info(details.result)
            raise exceptions.TestFail(details)

        warn_regex = settings.get_value('simpletests.status',
                                        'warn_regex',
                                        key_type='str',
                                        default=None)

        warn_location = settings.get_value('simpletests.status',
                                           'warn_location',
                                           default='all')

        skip_regex = settings.get_value('simpletests.status',
                                        'skip_regex',
                                        key_type='str',
                                        default=None)

        skip_location = settings.get_value('simpletests.status',
                                           'skip_location',
                                           default='all')

        # Keeping compatibility with 'avocado_warn' libexec
        for regex in [warn_regex, r'^\d\d:\d\d:\d\d WARN \|']:
            warn_msg = ("Test passed but there were warnings on %s during "
                        "execution. Check the log for details.")
            if regex is not None:
                re_warn = re.compile(regex, re.MULTILINE)
                if warn_location in ['all', 'stdout']:
                    if re_warn.search(result.stdout_text):
                        raise exceptions.TestWarn(warn_msg % 'stdout')

                if warn_location in ['all', 'stderr']:
                    if re_warn.search(result.stderr_text):
                        raise exceptions.TestWarn(warn_msg % 'stderr')

        if skip_regex is not None:
            re_skip = re.compile(skip_regex, re.MULTILINE)
            skip_msg = ("Test passed but %s indicates test was skipped. "
                        "Check the log for details.")

            if skip_location in ['all', 'stdout']:
                if re_skip.search(result.stdout_text):
                    raise exceptions.TestSkipError(skip_msg % 'stdout')

            if skip_location in ['all', 'stderr']:
                if re_skip.search(result.stderr_text):
                    raise exceptions.TestSkipError(skip_msg % 'stderr')

    def test(self):
        """
        Run the test and postprocess the results
        """
        self._execute_cmd()


class ExternalRunnerSpec(object):
    """
    Defines the basic options used by ExternalRunner
    """
    def __init__(self, runner, chdir=None, test_dir=None):
        self.runner = runner
        self.chdir = chdir
        self.test_dir = test_dir


class ExternalRunnerTest(SimpleTest):

    def __init__(self, name, params=None, base_logdir=None, job=None,
                 external_runner=None, external_runner_argument=None):
        if external_runner_argument is None:
            external_runner_argument = name.name
        if external_runner is None:
            raise ValueError("External runner test requires a valid "
                             "external_runner parameter, got None instead.")
        self.external_runner = external_runner
        super(ExternalRunnerTest, self).__init__(name, params, base_logdir,
                                                 job)
        self._command = "%s %s" % (external_runner.runner,
                                   external_runner_argument)

    @property
    def filename(self):
        return None

    def test(self):
        pre_cwd = os.getcwd()
        new_cwd = None
        try:
            self.log.info('Running test with the external test runner: "%s"',
                          self.external_runner.runner)

            # Change work directory if needed by the external runner
            if self.external_runner.chdir == 'runner':
                new_cwd = os.path.dirname(self.external_runner.runner)
            elif self.external_runner.chdir == 'test':
                new_cwd = self.external_runner.test_dir
            else:
                new_cwd = None
            if new_cwd is not None:
                self.log.debug('Changing working directory to "%s" '
                               'because of external runner requirements ',
                               new_cwd)
                os.chdir(new_cwd)

            self._execute_cmd()

        finally:
            if new_cwd is not None:
                os.chdir(pre_cwd)


class PythonUnittest(ExternalRunnerTest):
    """
    Python unittest test
    """
    def __init__(self, name, params=None, base_logdir=None, job=None,
                 test_dir=None, python_unittest_module=None):
        runner = "%s -m unittest -q -c" % sys.executable
        external_runner = ExternalRunnerSpec(runner, "test", test_dir)
        super(PythonUnittest, self).__init__(name, params, base_logdir, job,
                                             external_runner=external_runner,
                                             external_runner_argument=python_unittest_module)

    def _find_result(self, status="OK"):
        status_line = "[stderr] %s" % status
        with open(self.logfile) as logfile:
            lines = iter(logfile)
            for line in lines:
                if "[stderr] Ran 1 test in" in line:
                    break
            for line in lines:
                if status_line in line:
                    return line
        self.error("Fail to parse status from test result.")

    def test(self):
        try:
            super(PythonUnittest, self).test()
        except exceptions.TestFail:
            status = self._find_result("FAILED")
            if "errors" in status:
                self.error("Unittest reported error(s)")
            elif "failures" in status:
                self.fail("Unittest reported failure(s)")
            else:
                self.error("Unknown failure executing the unittest")
        status = self._find_result("OK")
        if "skipped" in status:
            self.cancel("Unittest reported skip")


class MockingTest(Test):

    """
    Class intended as generic substitute for avocado tests which will
    not be executed for some reason. This class is expected to be
    overridden by specific reason-oriented sub-classes.
    """

    def __init__(self, *args, **kwargs):
        """
        This class substitutes other classes. Let's just ignore the remaining
        arguments and only set the ones supported by avocado.Test
        """
        super_kwargs = dict()
        args = list(reversed(args))
        for arg in ["methodName", "name", "params", "base_logdir", "job",
                    "runner_queue"]:
            if arg in kwargs:
                super_kwargs[arg] = kwargs[arg]
            elif args:
                super_kwargs[arg] = args.pop()
        # The methodName might not exist, make sure it's self.test
        super_kwargs["methodName"] = "test"
        super(MockingTest, self).__init__(**super_kwargs)

    def test(self):
        pass


class TimeOutSkipTest(MockingTest):

    """
    Skip test due job timeout.

    This test is skipped due a job timeout.
    It will never have a chance to execute.
    """

    @skip('Test skipped due a job timeout!')
    def test(self):
        pass


class DryRunTest(MockingTest):

    """
    Fake test which logs itself and reports as CANCEL
    """

    def setUp(self):
        self.log.info("Test params:")
        for path, key, value in self.params.iteritems():
            self.log.info("%s:%s ==> %s", path, key, value)
        self.cancel('Test cancelled due to --dry-run')


class ReplaySkipTest(MockingTest):

    """
    Skip test due to job replay filter.

    This test is skipped due to a job replay filter.
    It will never have a chance to execute.
    """

    @skip('Test skipped due to a job replay filter!')
    def test(self):
        pass


class TestError(Test):
    """
    Generic test error.
    """

    def __init__(self, *args, **kwargs):
        exception = kwargs.pop('exception')
        Test.__init__(self, *args, **kwargs)
        self.exception = exception

    def test(self):
        self.error(self.exception)
