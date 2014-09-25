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

"""
Contains the base test implementation, used as a base for the actual
framework tests.
"""

import inspect
import logging
import os
import sys
import time
import traceback
import unittest
import tempfile

from avocado.core import data_dir
from avocado.core import exceptions
from avocado.utils import io
from avocado.utils import path
from avocado.utils import process
from avocado.utils.params import Params
from avocado import sysinfo
from avocado.version import VERSION

log = logging.getLogger("avocado.test")


def tb_info(exc_info):
    """
    Prepare traceback info.

    :param exc_info: Exception info produced by sys.exc_info()
    """
    exc_type, exc_value, exc_traceback = exc_info
    tb_info = traceback.format_exception(exc_type, exc_value,
                                         exc_traceback.tb_next)
    return tb_info


def log_exc_info(exc_info):
    """
    Log exception info.

    :param exc_info: Exception info produced by sys.exc_info()
    """
    log.error('')
    for line in tb_info(exc_info):
        for l in line.splitlines():
            log.error(l)
    log.error('')


def prepare_exc_info(exc_info):
    """
    Prepare traceback info.

    :param exc_info: Exception info produced by sys.exc_info()
    """
    return "".join(tb_info(exc_info))


class Test(unittest.TestCase):

    """
    Base implementation for the test class.

    You'll inherit from this to write your own tests. Tipically you'll want
    to implement setup(), action() and cleanup() methods on your own tests.
    """
    default_params = {}

    def __init__(self, methodName='runTest', name=None, params=None,
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
                            :func:`avocado.core.data_dir.get_job_logs_dir`.
        :param tag: Tag that differentiates 2 executions of the same test name.
                    Example: 'long', 'short', so we can differentiate
                    'sleeptest.long' and 'sleeptest.short'.
        :param job: The job that this test is part of.
        """
        if name is not None:
            self.name = name
        else:
            self.name = self.__class__.__name__

        if params is None:
            params = {}
        self.params = Params(params)
        self._raw_params = params

        shortname = self.params.get('shortname')
        s_tag = None
        if shortname:
            split_shortname = shortname.split('.')
            if len(split_shortname) > 1:
                s_tag = ".".join(split_shortname[1:])
        self.tag = tag or s_tag
        self.job = job

        basename = os.path.basename(self.name)

        if job is not None:
            tmpdir = tempfile.mkdtemp(dir=data_dir.get_tmp_dir(),
                                      prefix='job-%s-' % job.unique_id)
        else:
            tmpdir = tempfile.mkdtemp(dir=data_dir.get_tmp_dir())

        self.basedir = os.path.dirname(inspect.getfile(self.__class__))
        self.datadir = os.path.join(self.basedir, '%s.data' % basename)
        self.workdir = path.init_dir(tmpdir, basename)
        self.srcdir = path.init_dir(self.workdir, 'src')
        if base_logdir is None:
            base_logdir = data_dir.get_job_logs_dir()
        base_logdir = os.path.join(base_logdir, 'test-results')
        self.tagged_name = self.get_tagged_name(base_logdir)

        self.logdir = path.init_dir(base_logdir, self.tagged_name)
        io.set_log_file_dir(self.logdir)
        self.logfile = os.path.join(self.logdir, 'debug.log')

        self.stdout_file = os.path.join(self.logdir, 'stdout.actual')
        self.stderr_file = os.path.join(self.logdir, 'stderr.actual')

        self.outputdir = path.init_dir(self.logdir, 'data')
        self.sysinfodir = path.init_dir(self.logdir, 'sysinfo')
        self.sysinfo_logger = sysinfo.SysInfo(basedir=self.sysinfodir)

        self.log = logging.getLogger("avocado.test")

        self.stdout_log = logging.getLogger("avocado.test.stdout")
        self.stderr_log = logging.getLogger("avocado.test.stderr")

        self.log.info('START %s', self.tagged_name)
        self.log.debug('')
        self.log.debug('Test instance parameters:')

        # Set the helper set_default to the params object
        setattr(self.params, 'set_default', self._set_default)

        # Apply what comes from the params dict
        for key in sorted(self.params.keys()):
            self.log.debug('    %s = %s', key, self.params.get(key))
        self.log.debug('')

        # Apply what comes from the default_params dict
        self.log.debug('Default parameters:')
        for key in sorted(self.default_params.keys()):
            self.log.debug('    %s = %s', key, self.default_params.get(key))
            self.params.set_default(key, self.default_params[key])
        self.log.debug('')
        self.log.debug('Test instance params override defaults whenever available')
        self.log.debug('')

        # If there's a timeout set, log a timeout reminder
        if self.params.timeout:
            self.log.info('Test timeout set. Will wait %.2f s for '
                          'PID %s to end',
                          float(self.params.timeout), os.getpid())
            self.log.info('')

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
        unittest.TestCase.__init__(self)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return "Test(%r)" % self.tagged_name

    def tag_start(self):
        self.running = True
        self.time_start = time.time()

    def tag_end(self):
        self.running = False
        self.time_end = time.time()
        # for consistency sake, always use the same stupid method
        self.update_time_elapsed(self.time_end)

    def update_time_elapsed(self, current_time=None):
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
            self.update_time_elapsed()

        orig = dict(self.__dict__)
        d = {}
        preserve_attr = ['basedir', 'debugdir', 'depsdir', 'fail_class',
                         'fail_reason', 'logdir', 'logfile', 'name',
                         'resultsdir', 'srcdir', 'status', 'sysinfodir',
                         'tag', 'tagged_name', 'text_output', 'time_elapsed',
                         'traceback', 'workdir', 'whiteboard', 'time_start',
                         'time_end', 'running', 'paused', 'paused_msg']
        for key in sorted(orig):
            if key in preserve_attr:
                d[key] = orig[key]
        d['params'] = dict(orig['params'])
        d['class_name'] = self.__class__.__name__
        d['job_logdir'] = self.job.logdir
        d['job_unique_id'] = self.job.unique_id
        return d

    def _set_default(self, key, default):
        try:
            self.params[key]
        except Exception:
            self.params[key] = default

    def get_data_path(self, basename):
        """
        Find a test dependency path inside the test data dir.

        This is a short hand for an operation that will be commonly
        used on avocado tests, so we feel it deserves its own API.

        :param basename: Basename of the dep file. Ex: ``testsuite.tar.bz2``.

        :return: Path where dependency is supposed to be found.
        """
        return os.path.join(self.datadir, basename)

    def start_logging(self):
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

        self.stdout_file_handler = logging.FileHandler(filename=self.stdout_file)
        self.stdout_file_handler.setLevel(logging.DEBUG)
        self.stdout_file_handler.setFormatter(stream_formatter)
        self.stdout_log.addHandler(self.stdout_file_handler)

        self.stderr_file_handler = logging.FileHandler(filename=self.stderr_file)
        self.stderr_file_handler.setLevel(logging.DEBUG)
        self.stderr_file_handler.setFormatter(stream_formatter)
        self.stderr_log.addHandler(self.stderr_file_handler)

    def stop_logging(self):
        """
        Stop the logging activity of the test by cleaning the logger handlers.
        """
        self.log.removeHandler(self.file_handler)

    def get_tagged_name(self, logdir):
        """
        Get a test tagged name.

        If a test tag is defined, just return name.tag. If tag is absent,
        it'll try to find a tag that is not already taken (so there are no
        clashes in the results directory).

        :param logdir: Log directory being in use for result storage.

        :return: String `test.tag`.
        """
        if self.name.startswith('/'):
            self.name = self.name[1:]
        if self.tag is not None:
            return "%s.%s" % (self.name, self.tag)

        tag = 0
        if tag == 0:
            tagged_name = self.name
        else:
            tagged_name = "%s.%s" % (self.name, tag)
        test_logdir = os.path.join(logdir, tagged_name)
        while os.path.isdir(test_logdir):
            tag += 1
            tagged_name = "%s.%s" % (self.name, tag)
            test_logdir = os.path.join(logdir, tagged_name)
        self.tag = str(tag)

        return tagged_name

    def setup(self):
        """
        Setup stage that the test needs before passing to the actual action.

        Must be implemented by tests if they want such an stage. Commonly we'll
        download/compile test suites, create files needed for a test, among
        other possibilities.
        """
        pass

    def action(self):
        """
        Actual test payload. Must be implemented by tests.

        In case of an existing test suite wrapper, it'll execute the suite,
        or perform a series of operations, and based in the results of the
        operations decide if the test pass (let the test complete) or fail
        (raise a test related exception).
        """
        raise NotImplementedError('Test subclasses must implement an action '
                                  'method')

    def cleanup(self):
        """
        Cleanup stage after the action is done.

        Examples of cleanup actions are deleting temporary files, restoring
        firewall configurations or other system settings that were changed
        in setup.
        """
        pass

    def runTest(self, result=None):
        """
        Run test method, for compatibility with unittest.TestCase.

        :result: Unused param, compatibiltiy with :class:`unittest.TestCase`.
        """
        self.start_logging()
        self.sysinfo_logger.start_test_hook()
        action_exception = None
        cleanup_exception = None
        try:
            self.setup()
        except Exception, details:
            log_exc_info(sys.exc_info())
            raise exceptions.TestSetupFail(details)
        try:
            self.action()
        except Exception, details:
            log_exc_info(sys.exc_info())
            action_exception = details
        finally:
            try:
                self.cleanup()
            except Exception, details:
                log_exc_info(sys.exc_info())
                cleanup_exception = details
        # pylint: disable=E0702
        if action_exception is not None:
            raise action_exception
        elif cleanup_exception is not None:
            raise exceptions.TestSetupFail(cleanup_exception)

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

    def run_avocado(self, result=None):
        """
        Wraps the runTest metod, for execution inside the avocado runner.

        :result: Unused param, compatibiltiy with :class:`unittest.TestCase`.
        """
        self._setup_environment_variables()
        try:
            self.tag_start()
            self.runTest(result)
        except exceptions.TestBaseException, detail:
            self.status = detail.status
            self.fail_class = detail.__class__.__name__
            self.fail_reason = detail
            self.traceback = prepare_exc_info(sys.exc_info())
        except AssertionError, detail:
            self.status = 'FAIL'
            self.fail_class = detail.__class__.__name__
            self.fail_reason = detail
            self.traceback = prepare_exc_info(sys.exc_info())
        except Exception, detail:
            self.status = 'FAIL'
            self.fail_class = detail.__class__.__name__
            self.fail_reason = detail
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_info = traceback.format_exception(exc_type, exc_value,
                                                 exc_traceback.tb_next)
            self.traceback = "".join(tb_info)
            for e_line in tb_info:
                self.log.error(e_line)
        finally:
            self.tag_end()
            self.report()
            self.log.info("")
            with open(self.logfile, 'r') as log_file_obj:
                self.text_output = log_file_obj.read()
            self.stop_logging()

    def report(self):
        """
        Report result to the logging system.
        """
        if self.fail_reason is not None:
            self.log.error("%s %s -> %s: %s", self.status,
                           self.tagged_name,
                           self.fail_reason.__class__.__name__,
                           self.fail_reason)

        else:
            if self.status is None:
                self.status = 'INTERRUPTED'
            self.log.info("%s %s", self.status,
                          self.tagged_name)


class DropinTest(Test):

    """
    Run an arbitrary command that returns either 0 (PASS) or !=0 (FAIL).
    """

    def __init__(self, path, params=None, base_logdir=None, tag=None, job=None):
        self.path = os.path.abspath(path)
        super(DropinTest, self).__init__(name=path, base_logdir=base_logdir,
                                         params=params, tag=tag, job=job)

    def _log_detailed_cmd_info(self, result):
        """
        Log detailed command information.

        :param result: :class:`avocado.utils.process.CmdResult` instance.
        """
        run_info = str(result)
        for line in run_info.splitlines():
            self.log.info(line)

    def action(self):
        """
        Run the executable, and log its detailed execution.
        """
        try:
            result = process.run(self.path, verbose=True,
                                 record_stream_files=True)
            self._log_detailed_cmd_info(result)
        except exceptions.CmdError, details:
            self._log_detailed_cmd_info(details.result)
            raise exceptions.TestFail(details)


class MissingTest(Test):

    """
    Handle when there is no such test module in the test directory.
    """

    def __init__(self, name=None, params=None, base_logdir=None, tag=None,
                 job=None):
        super(MissingTest, self).__init__(name=name,
                                          base_logdir=base_logdir,
                                          tag=tag, job=job)

    def action(self):
        e_msg = ('Test %s could not be found in the test dir %s '
                 '(or test path does not exist)' %
                 (self.name, data_dir.get_test_dir()))
        raise exceptions.TestNotFoundError(e_msg)
