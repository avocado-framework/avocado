"""
Contains the base test implementation, used as a base for the actual
framework tests.
"""

import logging
import os
import time
from avocado.core import data_dir
from avocado.core import exceptions

log = logging.getLogger("avocado.test")


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
        self.workdir = os.path.join(self.basedir, 'work')
        self.srcdir = os.path.join(self.basedir, 'src')
        self.tmpdir = os.path.join(self.basedir, 'tmp')
        self.tagged_name = self.get_tagged_name(base_logdir, self.name,
                                                self.tag)
        self.logdir = os.path.join(base_logdir, self.tagged_name)
        if not os.path.isdir(self.logdir):
            os.makedirs(self.logdir)
        self.logfile = os.path.join(self.logdir, 'debug.log')
        self.sysinfodir = os.path.join(self.logdir, 'sysinfo')
        self.debugdir = None
        self.resultsdir = None
        self.status = None

        self.time_elapsed = None

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
