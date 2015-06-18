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
# Authors: Martin J Bligh <mbligh@google.com>, Andy Whitcroft <apw@shadowen.org>
import re

"""
Contains the base test implementation, used as a base for the actual
framework tests.
"""

import inspect
import logging
import os
import pipes
import shutil
import sys
import time

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from . import data_dir
from . import sysinfo
from . import exceptions
from . import multiplexer
from . import status
from .settings import settings
from .version import VERSION
from ..utils import genio
from ..utils import path as utils_path
from ..utils import process
from ..utils import stacktrace


class Test(unittest.TestCase):

    """
    Base implementation for the test class.

    You'll inherit from this to write your own tests. Typically you'll want
    to implement setUp(), test*() and tearDown() methods on your own tests.
    """
    default_params = {}

    def __init__(self, methodName='test', name=None, params=None,
                 base_logdir=None, tag=None, job=None, runner_queue=None):
        """
        Initializes the test.

        :param methodName: Name of the main method to run. For the sake of
                           compatibility with the original unittest class,
                           you should not set this.
        :param name: Pretty name of the test name. For normal tests, written
                     with the avocado API, this should not be set, this is
                     reserved for running random executables as tests.
        :param base_logdir: Directory where test logs should go. If None
                            provided, it'll use
                            :func:`avocado.data_dir.create_job_logs_dir`.
        :param tag: Tag that differentiates 2 executions of the same test name.
                    Example: 'long', 'short', so we can differentiate
                    'sleeptest.long' and 'sleeptest.short'.
        :param job: The job that this test is part of.
        """
        def record_and_warn(*args, **kwargs):
            """ Record call to this function and log warning """
            if not self.__log_warn_used:
                self.__log_warn_used = True
            return original_log_warn(*args, **kwargs)

        if name is not None:
            self.name = name
        else:
            self.name = self.__class__.__name__

        self.tag = tag or None

        self.job = job

        basename = os.path.basename(self.name)

        tmpdir = data_dir.get_tmp_dir()

        self.filename = inspect.getfile(self.__class__).rstrip('co')
        self.basedir = os.path.dirname(self.filename)
        self.datadir = self.filename + '.data'

        self.expected_stdout_file = os.path.join(self.datadir,
                                                 'stdout.expected')
        self.expected_stderr_file = os.path.join(self.datadir,
                                                 'stderr.expected')

        self.workdir = utils_path.init_dir(tmpdir, basename)
        self.srcdir = utils_path.init_dir(self.workdir, 'src')
        if base_logdir is None:
            base_logdir = data_dir.create_job_logs_dir()
        base_logdir = os.path.join(base_logdir, 'test-results')
        self.tagged_name = self.get_tagged_name(base_logdir)

        # Let's avoid trouble at logdir init time, since we're interested
        # in a relative directory here
        tagged_name = self.tagged_name
        if tagged_name.startswith('/'):
            tagged_name = tagged_name[1:]

        self.logdir = utils_path.init_dir(base_logdir, tagged_name)
        genio.set_log_file_dir(self.logdir)
        self.logfile = os.path.join(self.logdir, 'debug.log')

        self.stdout_file = os.path.join(self.logdir, 'stdout')
        self.stderr_file = os.path.join(self.logdir, 'stderr')

        self.outputdir = utils_path.init_dir(self.logdir, 'data')
        self.sysinfodir = utils_path.init_dir(self.logdir, 'sysinfo')
        self.sysinfo_logger = sysinfo.SysInfo(basedir=self.sysinfodir)

        self.log = logging.getLogger("avocado.test")
        original_log_warn = self.log.warning
        self.__log_warn_used = False
        self.log.warn = self.log.warning = record_and_warn

        self.stdout_log = logging.getLogger("avocado.test.stdout")
        self.stderr_log = logging.getLogger("avocado.test.stderr")

        mux_path = ['/test/*']
        if isinstance(params, dict):
            self.default_params = self.default_params.copy()
            self.default_params.update(params)
            params = []
        elif params is None:
            params = []
        elif isinstance(params, tuple):
            params, mux_path = params[0], params[1]
        self.params = multiplexer.AvocadoParams(params, self.name, self.tag,
                                                mux_path,
                                                self.default_params)

        self.log.info('START %s', self.tagged_name)

        self.debugdir = None
        self.resultsdir = None
        self.status = None
        self.fail_reason = None
        self.fail_class = None
        self.traceback = None
        self.text_output = None

        self.whiteboard = ''

        self.running = False
        self.time_start = None
        self.time_end = None
        self.paused = False
        self.paused_msg = ''

        self.runner_queue = runner_queue

        self.time_elapsed = None
        unittest.TestCase.__init__(self, methodName=methodName)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return "Test(%r)" % self.tagged_name

    def _tag_start(self):
        self.running = True
        self.time_start = time.time()

    def _tag_end(self):
        self.running = False
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
        preserve_attr = ['basedir', 'debugdir', 'depsdir',
                         'fail_reason', 'logdir', 'logfile', 'name',
                         'resultsdir', 'srcdir', 'status', 'sysinfodir',
                         'tag', 'tagged_name', 'text_output', 'time_elapsed',
                         'traceback', 'workdir', 'whiteboard', 'time_start',
                         'time_end', 'running', 'paused', 'paused_msg',
                         'fail_class', 'params']
        state = dict([(key, self.__dict__.get(key)) for key in preserve_attr])
        state['class_name'] = self.__class__.__name__
        state['job_logdir'] = self.job.logdir
        state['job_unique_id'] = self.job.unique_id
        return state

    def get_data_path(self, basename):
        """
        Find a test dependency path inside the test data dir.

        This is a short hand for an operation that will be commonly
        used on avocado tests, so we feel it deserves its own API.

        :param basename: Basename of the dep file. Ex: ``testsuite.tar.bz2``.

        :return: Path where dependency is supposed to be found.
        """
        return os.path.join(self.datadir, basename)

    def _register_log_file_handler(self, logger, formatter, filename,
                                   log_level=logging.DEBUG):
        file_handler = logging.FileHandler(filename=filename)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return file_handler

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

        self.stdout_file_handler = self._register_log_file_handler(self.stdout_log, stream_formatter,
                                                                   self.stdout_file)
        self.stderr_file_handler = self._register_log_file_handler(self.stderr_log, stream_formatter,
                                                                   self.stderr_file)

    def _stop_logging(self):
        """
        Stop the logging activity of the test by cleaning the logger handlers.
        """
        self.log.removeHandler(self.file_handler)

    def get_tagged_name(self, logdir):
        """
        Get a test tagged name.

        Combines name + tag (if present) to obtain unique name. When associated
        directory already exists, appends ".$number" until unused name
        is generated to avoid clashes.

        :param logdir: Log directory being in use for result storage.

        :return: Unique test name
        """
        name = self.name
        if self.tag is not None:
            name += ".%s" % self.tag
        tag = 0
        tagged_name = name
        while os.path.isdir(os.path.join(logdir, tagged_name)):
            tag += 1
            tagged_name = "%s.%s" % (name, tag)
        self.tag = "%s.%s" % (self.tag, tag) if self.tag else str(tag)

        return tagged_name

    def setUp(self):
        """
        Setup stage that the test needs before passing to the actual test*.

        Must be implemented by tests if they want such an stage. Commonly we'll
        download/compile test suites, create files needed for a test, among
        other possibilities.
        """
        pass

    def tearDown(self):
        """
        Cleanup stage after the test* is done.

        Examples of cleanup are deleting temporary files, restoring
        firewall configurations or other system settings that were changed
        in setup.
        """
        pass

    def record_reference_stdout(self):
        utils_path.init_dir(self.datadir)
        shutil.copyfile(self.stdout_file, self.expected_stdout_file)

    def record_reference_stderr(self):
        utils_path.init_dir(self.datadir)
        shutil.copyfile(self.stderr_file, self.expected_stderr_file)

    def check_reference_stdout(self):
        if os.path.isfile(self.expected_stdout_file):
            expected = genio.read_file(self.expected_stdout_file)
            actual = genio.read_file(self.stdout_file)
            msg = ('Actual test sdtout differs from expected one:\n'
                   'Actual:\n%s\nExpected:\n%s' % (actual, expected))
            self.assertEqual(expected, actual, msg)

    def check_reference_stderr(self):
        if os.path.isfile(self.expected_stderr_file):
            expected = genio.read_file(self.expected_stderr_file)
            actual = genio.read_file(self.stderr_file)
            msg = ('Actual test sdterr differs from expected one:\n'
                   'Actual:\n%s\nExpected:\n%s' % (actual, expected))
            self.assertEqual(expected, actual, msg)

    def _run_avocado(self):
        """
        Auxiliary method to run_avocado.
        """
        testMethod = getattr(self, self._testMethodName)
        self._start_logging()
        self.sysinfo_logger.start_test_hook()
        test_exception = None
        cleanup_exception = None
        stdout_check_exception = None
        stderr_check_exception = None
        try:
            self.setUp()
        except exceptions.TestNAError, details:
            stacktrace.log_exc_info(sys.exc_info(), logger='avocado.test')
            raise exceptions.TestNAError(details)
        except Exception, details:
            stacktrace.log_exc_info(sys.exc_info(), logger='avocado.test')
            raise exceptions.TestSetupFail(details)
        try:
            testMethod()
        except Exception, details:
            stacktrace.log_exc_info(sys.exc_info(), logger='avocado.test')
            test_exception = details
        finally:
            try:
                self.tearDown()
            except Exception, details:
                stacktrace.log_exc_info(sys.exc_info(), logger='avocado.test')
                cleanup_exception = details

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
                        self.check_reference_stdout()
                    except Exception, details:
                        stacktrace.log_exc_info(sys.exc_info(), logger='avocado.test')
                        stdout_check_exception = details
                    try:
                        self.check_reference_stderr()
                    except Exception, details:
                        stacktrace.log_exc_info(sys.exc_info(), logger='avocado.test')
                        stderr_check_exception = details
            elif not job_standalone:
                if output_check_record in ['all', 'stdout']:
                    self.record_reference_stdout()
                if output_check_record in ['all', 'stderr']:
                    self.record_reference_stderr()

        # pylint: disable=E0702
        if test_exception is not None:
            raise test_exception
        elif cleanup_exception is not None:
            raise exceptions.TestSetupFail(cleanup_exception)
        elif stdout_check_exception is not None:
            raise stdout_check_exception
        elif stderr_check_exception is not None:
            raise stderr_check_exception
        elif self.__log_warn_used:
            raise exceptions.TestWarn("Test passed but there were warnings "
                                      "during execution. Check the log for "
                                      "details.")

        self.status = 'PASS'
        self.sysinfo_logger.end_test_hook()

    def _setup_environment_variables(self):
        os.environ['AVOCADO_VERSION'] = VERSION
        os.environ['AVOCADO_TEST_BASEDIR'] = self.basedir
        os.environ['AVOCADO_TEST_DATADIR'] = self.datadir
        os.environ['AVOCADO_TEST_WORKDIR'] = self.workdir
        os.environ['AVOCADO_TEST_SRCDIR'] = self.srcdir
        os.environ['AVOCADO_TEST_LOGDIR'] = self.logdir
        os.environ['AVOCADO_TEST_LOGFILE'] = self.logfile
        os.environ['AVOCADO_TEST_OUTPUTDIR'] = self.outputdir
        os.environ['AVOCADO_TEST_SYSINFODIR'] = self.sysinfodir

    def run_avocado(self):
        """
        Wraps the run method, for execution inside the avocado runner.

        :result: Unused param, compatibility with :class:`unittest.TestCase`.
        """
        self._setup_environment_variables()
        try:
            self._tag_start()
            self._run_avocado()
        except exceptions.TestBaseException, detail:
            self.status = detail.status
            self.fail_class = detail.__class__.__name__
            self.fail_reason = detail
            self.traceback = stacktrace.prepare_exc_info(sys.exc_info())
        except AssertionError, detail:
            self.status = 'FAIL'
            self.fail_class = detail.__class__.__name__
            self.fail_reason = detail
            self.traceback = stacktrace.prepare_exc_info(sys.exc_info())
        except Exception, detail:
            stat = settings.get_value("runner.behavior",
                                      "uncaught_exception_result",
                                      default="ERROR")
            if stat not in status.mapping:
                stacktrace.log_message("Incorrect runner.behavior.generic_"
                                       "exception_result value '%s', using "
                                       "'ERROR' instead." % stat,
                                       "avocado.test")
                stat = "ERROR"
            self.status = stat
            tb_info = stacktrace.tb_info(sys.exc_info())
            self.traceback = stacktrace.prepare_exc_info(sys.exc_info())
            try:
                self.fail_class = str(detail.__class__.__name__)
                self.fail_reason = str(detail)
            except TypeError:
                self.fail_class = "Exception"
                self.fail_reason = ("Unable to get exception, check the "
                                    "traceback for details.")
            for e_line in tb_info:
                self.log.error(e_line)
        finally:
            self._tag_end()
            self._report()
            self.log.info("")
            with open(self.logfile, 'r') as log_file_obj:
                self.text_output = log_file_obj.read()
            self._stop_logging()

    def _report(self):
        """
        Report result to the logging system.
        """
        if self.fail_reason is not None:
            self.log.error("%s %s -> %s: %s", self.status,
                           self.tagged_name,
                           self.fail_class,
                           self.fail_reason)

        else:
            if self.status is None:
                self.status = 'INTERRUPTED'
            self.log.info("%s %s", self.status,
                          self.tagged_name)

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
        Skips the currently running test

        :param message: an optional message that will be recorded in the logs
        :type message: str
        """
        raise exceptions.TestNAError(message)


class SimpleTest(Test):

    """
    Run an arbitrary command that returns either 0 (PASS) or !=0 (FAIL).
    """

    re_avocado_log = re.compile(r'^\d\d:\d\d:\d\d DEBUG\| \[stdout\]'
                                r' \d\d:\d\d:\d\d WARN \|')

    def __init__(self, name, params=None, base_logdir=None, tag=None, job=None):
        self.path = os.path.abspath(name)
        super(SimpleTest, self).__init__(name=name, base_logdir=base_logdir,
                                         params=params, tag=tag, job=job)
        basedir = os.path.dirname(self.path)
        basename = os.path.basename(self.path)
        datadirname = basename + '.data'
        self.datadir = os.path.join(basedir, datadirname)
        self.expected_stdout_file = os.path.join(self.datadir,
                                                 'stdout.expected')
        self.expected_stderr_file = os.path.join(self.datadir,
                                                 'stderr.expected')

    def _log_detailed_cmd_info(self, result):
        """
        Log detailed command information.

        :param result: :class:`avocado.utils.process.CmdResult` instance.
        """
        self.log.info("Exit status: %s", result.exit_status)
        self.log.info("Duration: %s", result.duration)

    def test(self):
        """
        Run the executable, and log its detailed execution.
        """
        try:
            test_params = dict([(str(key), str(val)) for key, val in
                                self.params.iteritems()])
            # process.run uses shlex.split(), the self.path needs to be escaped
            result = process.run(pipes.quote(self.path), verbose=True,
                                 env=test_params)
            self._log_detailed_cmd_info(result)
        except process.CmdError, details:
            self._log_detailed_cmd_info(details.result)
            raise exceptions.TestFail(details)

    def run(self, result=None):
        super(SimpleTest, self).run(result)
        for line in open(self.logfile):
            if self.re_avocado_log.match(line):
                raise exceptions.TestWarn("Test passed but there were warnings"
                                          " on stdout during execution. Check "
                                          "the log for details.")


class MissingTest(Test):

    """
    Handle when there is no such test module in the test directory.
    """

    def test(self):
        e_msg = ('Test %s could not be found in the test dir %s '
                 '(or test path does not exist)' %
                 (self.name, data_dir.get_test_dir()))
        raise exceptions.TestNotFoundError(e_msg)


class BuggyTest(Test):

    """
    Used when the python module could not be imported.

    That means it is possibly a buggy test, but it could also be a random
    buggy python module.
    """

    def test(self):
        # pylint: disable=E0702
        raise self.params.get('exception')


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


class TimeOutSkipTest(Test):

    """
    Skip test due job timeout.

    This test is skipped due a job timeout.
    It will never have a chance to execute.
    """

    def test(self):
        e_msg = 'Test skipped due a job timeout!'
        raise exceptions.TestNAError(e_msg)
