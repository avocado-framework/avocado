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
# Authors: Lucas Meneghel Rodrigues <lmr@redhat.com>
#          Ruda Moura <rmoura@redhat.com>

"""
Contains the definition of the TestResult class, used for output in avocado.

It also contains the most basic test result class, HumanTestResult,
used by the test runner.
"""


class TestResult(object):

    """
    Test result class, holder for test result information.
    """

    def __init__(self, stream, args):
        """
        Creates an instance of TestResult.

        :param stream: an instance of :class:`avocado.core.output.OutputManager`.
        :param args: an instance of :class:`argparse.Namespace`.
        """
        self.stream = stream
        self.args = args
        self.tests_total = getattr(args, 'test_result_total', 1)
        self.tests_run = 0
        self.total_time = 0.0
        self.passed = []
        self.errors = []
        self.failed = []
        self.skipped = []
        self.warned = []

    def start_tests(self):
        """
        Called once before any tests are executed.
        """

        self.tests_run += 1

    def end_tests(self):
        """
        Called once after all tests are executed.
        """
        pass

    def start_test(self, test):
        """
        Called when the given test is about to run.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        pass

    def end_test(self, test):
        """
        Called when the given test has been run.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        self.tests_run += 1
        self.total_time += test.time_elapsed

    def add_pass(self, test):
        """
        Called when a test succeeded.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        self.passed.append(test)

    def add_error(self, test):
        """
        Called when a test had a setup error.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        self.errors.append(test)

    def add_fail(self, test):
        """
        Called when a test fails.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        self.failed.append(test)

    def add_skip(self, test):
        """
        Called when a test is skipped.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        self.skipped.append(test)

    def add_warn(self, test):
        """
        Called when a test had a warning.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        self.warned.append(test)

    def check_test(self, test):
        """
        Called once for a test to check status and report.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        status_map = {'PASS': self.add_pass,
                      'ERROR': self.add_error,
                      'FAIL': self.add_fail,
                      'TEST_NA': self.add_skip,
                      'WARN': self.add_warn}
        add = status_map[test.status]
        add(test)
        self.end_test(test)


class HumanTestResult(TestResult):

    """
    Human output Test result class.
    """

    def start_tests(self):
        """
        Called once before any tests are executed.
        """
        TestResult.start_tests(self)
        self.stream.log_header("DEBUG LOG: %s" % self.stream.debuglog)
        self.stream.log_header("TOTAL TESTS: %s" % self.tests_total)

    def end_tests(self):
        """
        Called once after all tests are executed.
        """
        self.stream.log_header("TOTAL PASSED: %d" % len(self.passed))
        self.stream.log_header("TOTAL ERROR: %d" % len(self.errors))
        self.stream.log_header("TOTAL FAILED: %d" % len(self.failed))
        self.stream.log_header("TOTAL SKIPPED: %d" % len(self.skipped))
        self.stream.log_header("TOTAL WARNED: %d" % len(self.warned))
        self.stream.log_header("ELAPSED TIME: %.2f s" % self.total_time)

    def start_test(self, test):
        """
        Called when the given test is about to run.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        self.test_label = '(%s/%s) %s: ' % (self.tests_run,
                                            self.tests_total,
                                            test.tagged_name)
        self.stream.info(msg=self.test_label, skip_newline=True)

    def end_test(self, test):
        """
        Called when the given test has been run.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        TestResult.end_test(self, test)

    def add_pass(self, test):
        """
        Called when a test succeeded.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        TestResult.add_pass(self, test)
        self.stream.log_pass(test.time_elapsed)

    def add_error(self, test):
        """
        Called when a test had a setup error.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        TestResult.add_error(self, test)
        self.stream.log_error(test.time_elapsed)

    def add_fail(self, test):
        """
        Called when a test fails.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        TestResult.add_fail(self, test)
        self.stream.log_fail(test.time_elapsed)

    def add_skip(self, test):
        """
        Called when a test is skipped.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        TestResult.add_skip(self, test)
        self.stream.log_skip(test.time_elapsed)

    def add_warn(self, test):
        """
        Called when a test had a warning.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        TestResult.add_warn(self, test)
        self.stream.log_warn(test.time_elapsed)
