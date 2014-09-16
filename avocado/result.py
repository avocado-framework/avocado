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


class InvalidOutputPlugin(Exception):
    pass


class TestResultProxy(object):

    def __init__(self):
        self.output_plugins = []

    def __getattr__(self, attr):
        for output_plugin in self.output_plugins:
            if hasattr(output_plugin, attr):
                return getattr(output_plugin, attr)
            else:
                return None

    def throbber_progress(self, progress_from_test=False):
        for output_plugin in self.output_plugins:
            if hasattr(output_plugin, 'throbber_progress'):
                output_plugin.throbber_progress(progress_from_test)

    def add_output_plugin(self, plugin):
        if not isinstance(plugin, TestResult):
            raise InvalidOutputPlugin("Object %s is not an instance of "
                                      "TestResult" % plugin)
        self.output_plugins.append(plugin)

    def start_tests(self):
        for output_plugin in self.output_plugins:
            output_plugin.start_tests()

    def end_tests(self):
        for output_plugin in self.output_plugins:
            output_plugin.end_tests()

    def start_test(self, state):
        for output_plugin in self.output_plugins:
            output_plugin.start_test(state)

    def end_test(self, state):
        for output_plugin in self.output_plugins:
            output_plugin.end_test(state)

    def add_pass(self, state):
        for output_plugin in self.output_plugins:
            output_plugin.add_pass(state)

    def add_error(self, state):
        for output_plugin in self.output_plugins:
            output_plugin.add_error(state)

    def add_not_found(self, state):
        for output_plugin in self.output_plugins:
            output_plugin.add_not_found(state)

    def add_fail(self, state):
        for output_plugin in self.output_plugins:
            output_plugin.add_fail(state)

    def add_skip(self, state):
        for output_plugin in self.output_plugins:
            output_plugin.add_skip(state)

    def add_warn(self, state):
        for output_plugin in self.output_plugins:
            output_plugin.add_warn(state)

    def check_test(self, state):
        for output_plugin in self.output_plugins:
            output_plugin.check_test(state)


class TestResult(object):

    """
    Test result class, holder for test result information.
    """

    #: Should be set by result plugins to inform users about output options
    #: inconsistencies given on the command line, and where these
    #: inconsistencies come from.
    command_line_arg_name = None

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
        self.not_found = []
        self.failed = []
        self.skipped = []
        self.warned = []
        # The convention is that a dash denotes stdout.
        self.output = '-'
        self.set_output()

    def set_output(self):
        """
        Set the value of the output attribute.

        By default, output is the stream (stdout), denoted by '-'.

        Must be implemented by plugins, so avocado knows where the plugin wants
        to output to, avoiding clashes among different plugins that want to
        use the stream at the same time.
        """
        pass



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

    def start_test(self, state):
        """
        Called when the given test is about to run.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        pass

    def end_test(self, state):
        """
        Called when the given test has been run.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        self.tests_run += 1
        self.total_time += state['time_elapsed']

    def add_pass(self, state):
        """
        Called when a test succeeded.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        self.passed.append(state)

    def add_error(self, state):
        """
        Called when a test had a setup error.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        self.errors.append(state)

    def add_not_found(self, state):
        """
        Called when a test was not found.

        Causes: non existing path or could not resolve alias.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        self.not_found.append(state)

    def add_fail(self, state):
        """
        Called when a test fails.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        self.failed.append(state)

    def add_skip(self, state):
        """
        Called when a test is skipped.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        self.skipped.append(state)

    def add_warn(self, state):
        """
        Called when a test had a warning.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        self.warned.append(state)

    def check_test(self, state):
        """
        Called once for a test to check status and report.

        :param test: A dict with test internal state
        """
        status_map = {'PASS': self.add_pass,
                      'ERROR': self.add_error,
                      'NOT_FOUND': self.add_not_found,
                      'FAIL': self.add_fail,
                      'TEST_NA': self.add_skip,
                      'WARN': self.add_warn}
        add = status_map[state['status']]
        add(state)
        self.end_test(state)


class HumanTestResult(TestResult):

    """
    Human output Test result class.
    """

    def start_tests(self):
        """
        Called once before any tests are executed.
        """
        TestResult.start_tests(self)
        self.stream.log_header("JOB ID    : %s" % self.stream.job_unique_id)
        self.stream.log_header("JOB LOG   : %s" % self.stream.logfile)
        self.stream.log_header("TESTS     : %s" % self.tests_total)

    def end_tests(self):
        """
        Called once after all tests are executed.
        """
        self.stream.log_header("PASS      : %d" % len(self.passed))
        self.stream.log_header("ERROR     : %d" % len(self.errors))
        self.stream.log_header("FAIL      : %d" % len(self.failed))
        self.stream.log_header("SKIP      : %d" % len(self.skipped))
        self.stream.log_header("WARN      : %d" % len(self.warned))
        self.stream.log_header("NOT FOUND : %d" % len(self.not_found))
        self.stream.log_header("TIME      : %.2f s" % self.total_time)

    def start_test(self, state):
        """
        Called when the given test is about to run.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        self.test_label = '(%s/%s) %s:  ' % (self.tests_run,
                                             self.tests_total,
                                             state['tagged_name'])
        self.stream.info(msg=self.test_label, skip_newline=True)

    def end_test(self, state):
        """
        Called when the given test has been run.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        TestResult.end_test(self, state)

    def add_pass(self, state):
        """
        Called when a test succeeded.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        TestResult.add_pass(self, state)
        self.stream.log_pass(state['time_elapsed'])

    def add_error(self, state):
        """
        Called when a test had a setup error.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        TestResult.add_error(self, state)
        self.stream.log_error(state['time_elapsed'])

    def add_not_found(self, state):
        """
        Called when a test was not found.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        TestResult.add_not_found(self, state)
        self.stream.log_not_found(state['time_elapsed'])

    def add_fail(self, state):
        """
        Called when a test fails.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        TestResult.add_fail(self, state)
        self.stream.log_fail(state['time_elapsed'])

    def add_skip(self, state):
        """
        Called when a test is skipped.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        TestResult.add_skip(self, state)
        self.stream.log_skip(state['time_elapsed'])

    def add_warn(self, state):
        """
        Called when a test had a warning.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        TestResult.add_warn(self, state)
        self.stream.log_warn(state['time_elapsed'])

    def throbber_progress(self, progress_from_test=False):
        self.stream.throbber_progress(progress_from_test)
