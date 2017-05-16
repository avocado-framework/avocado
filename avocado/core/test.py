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
import time
import unittest

from . import data_dir
from . import exceptions
from . import varianter
from . import sysinfo
from . import output
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


class NameNotTestNameError(Exception):

    """
    The given test name is not a TestName instance

    With the introduction of :class:`avocado.core.test.TestName`, it's
    not allowed to use other types as the ``name`` parameter to a test
    instance.  This exception is raised when this is attempted.
    """


class TestName(object):

    """
    Test name representation
    """

    def __init__(self, uid, name, variant=None, no_digits=None):
        """
        Test name according to avocado specification

        :param uid: unique test id (within the job)
        :param name: test name (identifies the executed test)
        :param variant: variant id
        :param no_digits: number of digits of the test uid
        """
        self.uid = uid
        if no_digits >= 0:
            self.str_uid = str(uid).zfill(no_digits if no_digits else 3)
        else:
            self.str_uid = str(uid)
        self.name = name or "<unknown>"
        self.variant = variant["variant_id"] if variant else None
        if variant is None:
            self.str_variant = ""
        else:
            self.str_variant = (";" + str(variant["variant_id"])
                                if variant["variant_id"] else "")

    def __str__(self):
        return "%s-%s%s" % (self.str_uid, self.name, self.str_variant)

    def __repr__(self):
        return repr(str(self))

    def __eq__(self, other):
        if isinstance(other, basestring):
            return str(self) == other
        else:
            return self.__dict__ == other.__dict__

    def str_filesystem(self):
        """
        File-system friendly representation of the test name
        """
        name = str(self)
        fsname = astring.string_to_safe_path(name)
        if len(name) == len(fsname):    # everything fits in
            return fsname
        # 001-mytest;foo
        # 001-mytest;f
        # 001-myte;foo
        idx_fit_variant = len(fsname) - len(self.str_variant)
        if idx_fit_variant > len(self.str_uid):     # full uid+variant
            return (fsname[:idx_fit_variant] +
                    astring.string_to_safe_path(self.str_variant))
        elif len(self.str_uid) <= len(fsname):   # full uid
            return astring.string_to_safe_path(self.str_uid + self.str_variant)
        else:       # not even uid could be stored in fs
            raise AssertionError("Test uid is too long to be stored on the "
                                 "filesystem: %s\nFull test name is %s"
                                 % (self.str_uid, str(self)))


class Test(unittest.TestCase):

    """
    Base implementation for the test class.

    You'll inherit from this to write your own tests. Typically you'll want
    to implement setUp(), test*() and tearDown() methods on your own tests.
    """
    #: `default_params` will be deprecated by the end of 2017.
    default_params = {}
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
                 base_logdir=None, job=None, runner_queue=None):
        """
        Initializes the test.

        :param methodName: Name of the main method to run. For the sake of
                           compatibility with the original unittest class,
                           you should not set this.
        :param name: Pretty name of the test name. For normal tests,
                     written with the avocado API, this should not be
                     set.  This is reserved for internal Avocado use,
                     such as when running random executables as tests.
        :type name: :class:`avocado.core.test.TestName`
        :param base_logdir: Directory where test logs should go. If None
                            provided, it'll use
                            :func:`avocado.data_dir.create_job_logs_dir`.
        :param job: The job that this test is part of.
        :raises: :class:`avocado.core.test.NameNotTestNameError`
        """
        def record_and_warn(*args, **kwargs):
            """ Record call to this function and log warning """
            if not self.__log_warn_used:
                self.__log_warn_used = True
            return original_log_warn(*args, **kwargs)

        if name is not None:
            if not isinstance(name, TestName):
                raise NameNotTestNameError(name)
            self.__name = name
        else:
            self.__name = TestName(0, self.__class__.__name__)

        self.__job = job

        if self.datadir is None:
            self._expected_stdout_file = None
            self._expected_stderr_file = None
        else:
            self._expected_stdout_file = os.path.join(self.datadir,
                                                      'stdout.expected')
            self._expected_stderr_file = os.path.join(self.datadir,
                                                      'stderr.expected')

        if base_logdir is None:
            base_logdir = data_dir.create_job_logs_dir()
        base_logdir = os.path.join(base_logdir, 'test-results')
        logdir = os.path.join(base_logdir, self.name.str_filesystem())
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

        mux_path = ['/test/*']
        if isinstance(params, dict):
            self.default_params = self.default_params.copy()
            self.default_params.update(params)
            params = []
        elif params is None:
            params = []
        elif isinstance(params, tuple):
            params, mux_path = params[0], params[1]
        self.__params = varianter.AvocadoParams(params, self.name,
                                                mux_path,
                                                self.default_params)
        default_timeout = getattr(self, "timeout", None)
        self.timeout = self.params.get("timeout", default=default_timeout)

        self.log.info('START %s', self.name)

        self.__status = None
        self.__fail_reason = None
        self.__fail_class = None
        self.__traceback = None

        self.__running = False
        self.paused = False
        self.paused_msg = ''

        self.__runner_queue = runner_queue

        unittest.TestCase.__init__(self, methodName=methodName)

    @property
    def name(self):
        """
        The test name (TestName instance)
        """
        return self.__name

    @property
    def job(self):
        """
        The job this test is associated with
        """
        return self.__job

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
    def datadir(self):
        """
        Returns the path to the directory that contains test data files
        """
        # Maximal allowed file name length is 255
        if (self.filename is not None and
                len(os.path.basename(self.filename)) < 251):
            return self.filename + '.data'
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

    @data_structures.LazyProperty
    def workdir(self):
        basename = (os.path.basename(self.logdir).replace(':', '_')
                    .replace(';', '_'))
        return utils_path.init_dir(data_dir.get_tmp_dir(), basename)

    @data_structures.LazyProperty
    def srcdir(self):
        return utils_path.init_dir(self.workdir, 'src')

    @data_structures.LazyProperty
    def cache_dirs(self):
        """
        Returns a list of cache directories as set in config file.
        """
        cache_dirs = settings.get_value('datadir.paths', 'cache_dirs',
                                        key_type=list, default=[])
        datadir_cache = os.path.join(data_dir.get_data_dir(), 'cache')
        if datadir_cache not in cache_dirs:
            cache_dirs.append(datadir_cache)
        return cache_dirs

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
        self.assertTrue(self.__runner_queue is None, "Overriding of runner_"
                        "queue multiple times is not allowed -> old=%s new=%s"
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
        preserve_attr = ['basedir', 'fail_reason',
                         'logdir', 'logfile', 'name', 'srcdir',
                         'status', 'time_elapsed',
                         'traceback', 'workdir', 'whiteboard', 'time_start',
                         'time_end', 'running', 'paused', 'paused_msg',
                         'fail_class', 'params', "timeout"]
        state = {key: getattr(self, key, None) for (key) in preserve_attr}
        state['class_name'] = self.__class__.__name__
        state['job_logdir'] = self.job.logdir
        state['job_unique_id'] = self.job.unique_id
        return state

    def _register_log_file_handler(self, logger, formatter, filename,
                                   log_level=logging.DEBUG):
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

        self._register_log_file_handler(log_test_stdout,
                                        stream_formatter,
                                        self._stdout_file)
        self._register_log_file_handler(log_test_stderr,
                                        stream_formatter,
                                        self._stderr_file)
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
        for name, handler in self._logging_handlers.iteritems():
            logging.getLogger(name).removeHandler(handler)

    def _record_reference_stdout(self):
        if self.datadir is not None:
            utils_path.init_dir(self.datadir)
            shutil.copyfile(self._stdout_file, self._expected_stdout_file)

    def _record_reference_stderr(self):
        if self.datadir is not None:
            utils_path.init_dir(self.datadir)
            shutil.copyfile(self._stderr_file, self._expected_stderr_file)

    def _check_reference_stdout(self):
        if (self._expected_stdout_file is not None and
                os.path.isfile(self._expected_stdout_file)):
            expected = genio.read_file(self._expected_stdout_file)
            actual = genio.read_file(self._stdout_file)
            msg = ('Actual test sdtout differs from expected one:\n'
                   'Actual:\n%s\nExpected:\n%s' % (actual, expected))
            self.assertEqual(expected, actual, msg)

    def _check_reference_stderr(self):
        if (self._expected_stderr_file is not None and
                os.path.isfile(self._expected_stderr_file)):
            expected = genio.read_file(self._expected_stderr_file)
            actual = genio.read_file(self._stderr_file)
            msg = ('Actual test sdterr differs from expected one:\n'
                   'Actual:\n%s\nExpected:\n%s' % (actual, expected))
            self.assertEqual(expected, actual, msg)

    def _run_avocado(self):
        """
        Auxiliary method to run_avocado.
        """
        testMethod = getattr(self, self._testMethodName)
        self._start_logging()
        if self.__sysinfo_enabled:
            self.__sysinfo_logger.start_test_hook()
        test_exception = None
        cleanup_exception = None
        stdout_check_exception = None
        stderr_check_exception = None
        skip_test = getattr(testMethod, '__skip_test_decorator__', False)
        cancel_test = False
        try:
            if skip_test is False:
                self.setUp()
        except (exceptions.TestSetupSkip, exceptions.TestSkipError) as details:
            stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
            raise exceptions.TestSkipError(details)
        except exceptions.TestCancel as details:
            cancel_test = details
        except:  # Old-style exceptions are not inherited from Exception()
            stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
            details = sys.exc_info()[1]
            raise exceptions.TestSetupFail(details)
        try:
            if cancel_test:
                raise exceptions.TestCancel(cancel_test)

            testMethod()
        except exceptions.TestSetupSkip as details:
            stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
            skip_illegal_msg = ('Calling skip() in places other than '
                                'setUp() is not allowed in avocado, you '
                                'must fix your test. Original skip exception: '
                                '%s' % details)
            raise exceptions.TestError(skip_illegal_msg)
        except exceptions.TestSkipError as details:
            stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
            raise
        except exceptions.TestCancel as details:
            stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
            raise
        except:  # Old-style exceptions are not inherited from Exception()
            stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
            details = sys.exc_info()[1]
            if not isinstance(details, Exception):  # Avoid passing nasty exc
                details = exceptions.TestError("%r: %s" % (details, details))
            test_exception = details
            self.log.debug("Local variables:")
            local_vars = inspect.trace()[1][0].f_locals
            for key, value in local_vars.iteritems():
                self.log.debug(' -> %s %s: %s', key, type(value), value)
        finally:
            try:
                if skip_test is False:
                    self.tearDown()
            except exceptions.TestSetupSkip as details:
                stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
                skip_illegal_msg = ('Calling skip() in places other than '
                                    'setUp() is not allowed in avocado, '
                                    'you must fix your test. Original skip '
                                    'exception: %s' % details)
                raise exceptions.TestError(skip_illegal_msg)
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
            except:  # avoid old-style exception failures
                stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
                details = sys.exc_info()[1]
                cleanup_exception = exceptions.TestSetupFail(details)

        whiteboard_file = os.path.join(self.logdir, 'whiteboard')
        genio.write_file(whiteboard_file, self.whiteboard)

        if self.job is not None:
            job_standalone = getattr(self.job.args, 'standalone', False)
            output_check_record = getattr(self.job.args,
                                          'output_check_record', 'none')
            no_record_mode = (not job_standalone and
                              output_check_record == 'none')
            disable_output_check = (not job_standalone and
                                    getattr(self.job.args,
                                            'output_check', 'on') == 'off')

            if job_standalone or no_record_mode:
                if not disable_output_check:
                    try:
                        self._check_reference_stdout()
                    except Exception as details:
                        stacktrace.log_exc_info(sys.exc_info(),
                                                logger=LOG_JOB)
                        stdout_check_exception = details
                    try:
                        self._check_reference_stderr()
                    except Exception as details:
                        stacktrace.log_exc_info(sys.exc_info(),
                                                logger=LOG_JOB)
                        stderr_check_exception = details
            elif not job_standalone:
                if output_check_record in ['all', 'stdout']:
                    self._record_reference_stdout()
                if output_check_record in ['all', 'stderr']:
                    self._record_reference_stderr()

        # pylint: disable=E0702
        if test_exception is not None:
            raise test_exception
        elif cleanup_exception is not None:
            raise cleanup_exception
        elif stdout_check_exception is not None:
            raise stdout_check_exception
        elif stderr_check_exception is not None:
            raise stderr_check_exception
        elif self.__log_warn_used:
            raise exceptions.TestWarn("Test passed but there were warnings "
                                      "during execution. Check the log for "
                                      "details.")

        self.__status = 'PASS'
        if self.__sysinfo_enabled:
            self.__sysinfo_logger.end_test_hook()

    def _setup_environment_variables(self):
        os.environ['AVOCADO_VERSION'] = VERSION
        if self.basedir is not None:
            os.environ['AVOCADO_TEST_BASEDIR'] = self.basedir
        if self.datadir is not None:
            os.environ['AVOCADO_TEST_DATADIR'] = self.datadir
        os.environ['AVOCADO_TEST_WORKDIR'] = self.workdir
        os.environ['AVOCADO_TEST_SRCDIR'] = self.srcdir
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
            self.__fail_reason = detail
            self.__traceback = stacktrace.prepare_exc_info(sys.exc_info())
        except AssertionError as detail:
            self.__status = 'FAIL'
            self.__fail_class = detail.__class__.__name__
            self.__fail_reason = detail
            self.__traceback = stacktrace.prepare_exc_info(sys.exc_info())
        except Exception as detail:
            self.__status = 'ERROR'
            tb_info = stacktrace.tb_info(sys.exc_info())
            self.__traceback = stacktrace.prepare_exc_info(sys.exc_info())
            try:
                self.__fail_class = str(detail.__class__.__name__)
                self.__fail_reason = str(detail)
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

    def skip(self, message=None):
        """
        Skips the currently running test.

        This method should only be called from a test's setUp() method, not
        anywhere else, since by definition, if a test gets to be executed, it
        can't be skipped anymore. If you call this method outside setUp(),
        avocado will mark your test status as ERROR, and instruct you to
        fix your test in the error message.

        :param message: an optional message that will be recorded in the logs
        :type message: str
        """
        dep_msg = "WARNING: self.skip() will be deprecated. " \
                  "Use 'self.cancel()' or the skip decorators"
        raise exceptions.TestSetupSkip("[%s] %s" % (dep_msg, message))

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

    def fetch_asset(self, name, asset_hash=None, algorithm='sha1',
                    locations=None, expire=None):
        """
        Method o call the utils.asset in order to fetch and asset file
        supporting hash check, caching and multiple locations.

        :param name: the asset filename or URL
        :param asset_hash: asset hash (optional)
        :param algorithm: hash algorithm (optional, defaults to sha1)
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

    re_avocado_log = re.compile(r'^\d\d:\d\d:\d\d DEBUG\| \[stdout\]'
                                r' \d\d:\d\d:\d\d WARN \|')

    def __init__(self, name, params=None, base_logdir=None, job=None):
        super(SimpleTest, self).__init__(name=name, params=params,
                                         base_logdir=base_logdir, job=job)
        self._command = None
        if self.filename is not None:
            self._command = pipes.quote(self.filename)

    @property
    def filename(self):
        """
        Returns the name of the file (path) that holds the current test
        """
        return os.path.abspath(self.name.name)

    def _log_detailed_cmd_info(self, result):
        """
        Log detailed command information.

        :param result: :class:`avocado.utils.process.CmdResult` instance.
        """
        self.log.info("Exit status: %s", result.exit_status)
        self.log.info("Duration: %s", result.duration)

    def execute_cmd(self):
        """
        Run the executable, and log its detailed execution.
        """
        try:
            test_params = dict([(str(key), str(val)) for _, key, val in
                                self.params.iteritems()])

            # process.run uses shlex.split(), the self.path needs to be escaped
            result = process.run(self._command, verbose=True,
                                 env=test_params)

            self._log_detailed_cmd_info(result)
        except process.CmdError as details:
            self._log_detailed_cmd_info(details.result)
            raise exceptions.TestFail(details)
        for line in open(self.logfile):
            if self.re_avocado_log.match(line):
                raise exceptions.TestWarn("Test passed but there were warnings"
                                          " on stdout during execution. Check "
                                          "the log for details.")

    def test(self):
        """
        Run the test and postprocess the results
        """
        self.execute_cmd()


class ExternalRunnerTest(SimpleTest):

    def __init__(self, name, params=None, base_logdir=None, job=None,
                 external_runner=None):
        self.assertIsNotNone(external_runner, "External runner test requires "
                             "external_runner parameter, got None instead.")
        self.external_runner = external_runner
        super(ExternalRunnerTest, self).__init__(name, params, base_logdir,
                                                 job)
        self._command = external_runner.runner + " " + self.name.name

    @property
    def filename(self):
        return None

    def test(self):
        pre_cwd = os.getcwd()
        new_cwd = None
        try:
            self.log.info('Running test with the external level test '
                          'runner: "%s"', self.external_runner.runner)

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

            self.execute_cmd()

        finally:
            if new_cwd is not None:
                os.chdir(pre_cwd)


class MissingTest(Test):

    """
    Handle when there is no such test module in the test directory.
    """

    def test(self):
        e_msg = ('Test %s could not be found in the test dir %s '
                 '(or test path does not exist)' %
                 (self.name, data_dir.get_test_dir()))
        raise exceptions.TestNotFoundError(e_msg)


class NotATest(Test):

    """
    The file is not a test.

    Either a non executable python module with no avocado test class in it,
    or a regular, non executable file.
    """

    def test(self):
        e_msg = ('File %s is not executable and does not contain an avocado '
                 'test class in it ' % self.name)
        raise exceptions.NotATestError(e_msg)


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
