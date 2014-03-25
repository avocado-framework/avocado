"""
Contains the base test implementation, used as a base for the actual
framework tests.
"""

import logging
import os
import sys
import time
import traceback
from avocado.core import data_dir
from avocado.core import exceptions
from avocado.utils import process


class Test(object):

    """
    Base implementation for the test class.

    You'll inherit from this to write your own tests. Tipically you'll want
    to implement setup(), action() and cleanup() methods on your own tests.
    """

    def __init__(self, name, base_logdir, tag=None):
        """
        Initializes the test.

        :param name: Test Name. Example: 'sleeptest'.
        :param tag: Tag that differentiates 2 executions of the same test name.
                Example: 'long', 'short', so we can differentiate
                'sleeptest.long' and 'sleeptest.short'.

        Test Attributes:
        basedir: Where the test .py file is located (root dir).
        depsdir: If this is an existing test suite wrapper, it'll contain the
                test suite sources and other auxiliary files. Usually inside
                basedir, 'deps' subdirectory.
        workdir: Place where temporary copies of the source code, binaries,
                image files will be created and modified.
        base_logdir: Base log directory, where logs from all tests go to.
        """
        self.name = name
        self.tag = tag
        self.basedir = os.path.join(data_dir.get_test_dir(), name)
        self.depsdir = os.path.join(self.basedir, 'deps')
        self.workdir = os.path.join(data_dir.get_tmp_dir(), self.name)
        if not os.path.isdir(self.workdir):
            os.makedirs(self.workdir)
        self.srcdir = os.path.join(self.workdir, 'src')
        if not os.path.isdir(self.srcdir):
            os.makedirs(self.srcdir)
        self.tagged_name = self.get_tagged_name(base_logdir, self.name,
                                                self.tag)
        self.logdir = os.path.join(base_logdir, self.tagged_name)
        if not os.path.isdir(self.logdir):
            os.makedirs(self.logdir)
        self.logfile = os.path.join(self.logdir, 'debug.log')
        self.sysinfodir = os.path.join(self.logdir, 'sysinfo')

        self.log = logging.getLogger("avocado.test")

        self.debugdir = None
        self.resultsdir = None
        self.status = None
        self.fail_reason = None

        self.time_elapsed = None

    def get_deps_path(self, basename):
        return os.path.join(self.depsdir, basename)

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

    def stop_logging(self):
        self.log.removeHandler(self.file_handler)

    def get_tagged_name(self, logdir, name, tag):
        if tag is not None:
            return "%s.%s" % (self.name, self.tag)
        tag = 1
        tagged_name = "%s.%s" % (name, tag)
        test_logdir = os.path.join(logdir, tagged_name)
        while os.path.isdir(test_logdir):
            tag += 1
            tagged_name = "%s.%s" % (name, tag)
            test_logdir = os.path.join(logdir, tagged_name)
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

    def run(self):
        """
        Main test execution entry point.

        It'll run the action payload, taking into consideration profiling
        requirements. After the test is done, it reports time and status.
        """
        start_time = time.time()
        try:
            self.action()
            self.status = 'PASS'
        except exceptions.TestBaseException, detail:
            self.status = detail.status
            self.fail_reason = detail
        except Exception, detail:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_info = traceback.format_exception(exc_type, exc_value,
                                                 exc_traceback.tb_next)
            tb_info = "".join(tb_info)
            for e_line in tb_info.splitlines():
                self.log.error(e_line)
            self.status = 'FAIL'
            self.fail_reason = detail
        finally:
            end_time = time.time()
            self.time_elapsed = end_time - start_time

        return self.status == 'PASS'

    def cleanup(self):
        """
        Cleanup stage after the action is done.

        Examples of cleanup actions are deleting temporary files, restoring
        firewall configurations or other system settings that were changed
        in setup.
        """
        pass

    def report(self):
        if self.fail_reason is not None:
            self.log.error("%s %s -> %s: %s", self.status,
                           self.tagged_name,
                           self.fail_reason.__class__.__name__,
                           self.fail_reason)

        else:
            self.log.info("%s %s", self.status,
                          self.tagged_name)


class DropinTest(Test):

    """
    Run an arbitrary command that returns either 0 (PASS) or !=0 (FAIL).
    """

    def __init__(self, path, base_logdir, tag=None):
        basename = os.path.basename(path)
        name = basename.split(".")[0]
        self.path = os.path.abspath(path)
        super(DropinTest, self).__init__(name, base_logdir, tag)

    def _log_detailed_cmd_info(self, result):
        run_info = str(result)
        for line in run_info.splitlines():
            self.log.info(line)

    def action(self):
        try:
            result = process.run(self.path, verbose=True)
            self._log_detailed_cmd_info(result)
        except exceptions.CmdError, details:
            self._log_detailed_cmd_info(details.result)
            raise exceptions.TestFail(details)
