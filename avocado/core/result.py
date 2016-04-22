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

import os
import logging

from . import output


class InvalidOutputPlugin(Exception):
    pass


def register_test_result_class(application_args, klass):
    """
    Register the given test result class to be loaded and enabled by the job

    :param application_args: the parsed application command line arguments.
                             This is currently being abused to hold various job
                             settings and feature choices, such as the runner.
    :type application_args: :class:`argparse.Namespace`
    :param klass: the test result class to enable
    :type klass: a subclass of :class:`TestResult`
    """
    if not hasattr(application_args, 'test_result_classes'):
        application_args.test_result_classes = set()
    application_args.test_result_classes.add(klass)


class TestResultProxy(object):

    def __init__(self):
        self.output_plugins = []

    def notify_progress(self, progress_from_test=False):
        for output_plugin in self.output_plugins:
            if hasattr(output_plugin, 'notify_progress'):
                output_plugin.notify_progress(progress_from_test)

    def add_output_plugin(self, plugin):
        if not isinstance(plugin, TestResult):
            raise InvalidOutputPlugin("Object %s is not an instance of "
                                      "TestResult" % plugin)
        self.output_plugins.append(plugin)

    def output_plugins_using_stdout(self):
        using_stdout = []
        for op in self.output_plugins:
            if op.output == '-':
                using_stdout.append(op.command_line_arg_name)
        return using_stdout

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

    def __init__(self, job):
        """
        Creates an instance of TestResult.

        :param job: an instance of :class:`avocado.core.job.Job`.
        """
        self.job_unique_id = getattr(job, "unique_id", None)
        self.logfile = getattr(job, "logfile", None)
        self.args = getattr(job, "args", None)
        self.tests_total = getattr(self.args, 'test_result_total', 1)
        self.tests_run = 0
        self.total_time = 0.0
        self.passed = []
        self.errors = []
        self.failed = []
        self.skipped = []
        self.warned = []
        self.interrupted = []

        # Where this results intends to write to. Convention is that a dash (-)
        # means stdout, and stdout is a special output that can be exclusively
        # claimed by a result class.
        self.output = None

    def _reconcile(self):
        """
        Make sure job results are reconciled

        In situations such as job interruptions, some test results will be
        missing, but this is no excuse for giving wrong summaries of test
        results.
        """
        valid_results_count = (len(self.passed) + len(self.errors) +
                               len(self.failed) + len(self.warned) +
                               len(self.skipped) + len(self.interrupted))
        other_skipped_count = self.tests_total - valid_results_count
        for i in xrange(other_skipped_count):
            self.skipped.append({})

    def start_tests(self):
        """
        Called once before any tests are executed.
        """
        self.tests_run += 1

    def end_tests(self):
        """
        Called once after all tests are executed.
        """
        self._reconcile()

    def start_test(self, state):
        """
        Called when the given test is about to run.

        :param state: result of :class:`avocado.core.test.Test.get_state`.
        :type state: dict
        """
        pass

    def end_test(self, state):
        """
        Called when the given test has been run.

        :param state: result of :class:`avocado.core.test.Test.get_state`.
        :type state: dict
        """
        self.tests_run += 1
        self.total_time += state['time_elapsed']

    def add_pass(self, state):
        """
        Called when a test succeeded.

        :param state: result of :class:`avocado.core.test.Test.get_state`.
        :type state: dict
        """
        self.passed.append(state)

    def add_error(self, state):
        """
        Called when a test had a setup error.

        :param state: result of :class:`avocado.core.test.Test.get_state`.
        :type state: dict
        """
        self.errors.append(state)

    def add_fail(self, state):
        """
        Called when a test fails.

        :param state: result of :class:`avocado.core.test.Test.get_state`.
        :type state: dict
        """
        self.failed.append(state)

    def add_skip(self, state):
        """
        Called when a test is skipped.

        :param test: an instance of :class:`avocado.core.test.Test`.
        """
        self.skipped.append(state)

    def add_warn(self, state):
        """
        Called when a test had a warning.

        :param state: result of :class:`avocado.core.test.Test.get_state`.
        :type state: dict
        """
        self.warned.append(state)

    def add_interrupt(self, state):
        """
        Called when a test is interrupted by the user.

        :param state: result of :class:`avocado.core.test.Test.get_state`.
        :type state: dict
        """
        self.interrupted.append(state)

    def check_test(self, state):
        """
        Called once for a test to check status and report.

        :param test: A dict with test internal state
        """
        status_map = {'PASS': self.add_pass,
                      'ERROR': self.add_error,
                      'FAIL': self.add_fail,
                      'SKIP': self.add_skip,
                      'WARN': self.add_warn,
                      'INTERRUPTED': self.add_interrupt}
        add = status_map[state['status']]
        add(state)
        self.end_test(state)


class HumanTestResult(TestResult):

    """
    Human output Test result class.
    """

    def __init__(self, job):
        super(HumanTestResult, self).__init__(job)
        self.log = logging.getLogger("avocado.app")
        self.__throbber = output.Throbber()

    def start_tests(self):
        """
        Called once before any tests are executed.
        """
        super(HumanTestResult, self).start_tests()
        self.log.info("JOB ID     : %s", self.job_unique_id)
        if getattr(self.args, "replay_sourcejob", None):
            self.log.info("SRC JOB ID : %s", self.args.replay_sourcejob)
        self.log.info("JOB LOG    : %s", self.logfile)
        self.log.info("TESTS      : %s", self.tests_total)

    def end_tests(self):
        """
        Called once after all tests are executed.
        """
        super(HumanTestResult, self).end_tests()
        self.log.info("RESULTS    : PASS %d | ERROR %d | FAIL %d | SKIP %d | "
                      "WARN %d | INTERRUPT %s", len(self.passed),
                      len(self.errors), len(self.failed), len(self.skipped),
                      len(self.warned), len(self.interrupted))
        if self.args is not None:
            if 'html_output' in self.args:
                logdir = os.path.dirname(self.logfile)
                html_file = os.path.join(logdir, 'html', 'results.html')
                self.log.info("JOB HTML   : %s", html_file)
        self.log.info("TIME       : %.2f s", self.total_time)

    def start_test(self, state):
        super(HumanTestResult, self).start_test(state)
        name = state["name"]
        self.log.debug(' (%s/%s) %s:  ', name.str_uid, self.tests_total,
                       name.name + name.str_variant,
                       extra={"skip_newline": True})

    def end_test(self, state):
        super(HumanTestResult, self).end_test(state)
        status = state["status"]
        if status == "TEST_NA":
            status = "SKIP"
        mapping = {'PASS': output.TERM_SUPPORT.PASS,
                   'ERROR': output.TERM_SUPPORT.ERROR,
                   'FAIL': output.TERM_SUPPORT.FAIL,
                   'SKIP': output.TERM_SUPPORT.SKIP,
                   'WARN': output.TERM_SUPPORT.WARN,
                   'INTERRUPTED': output.TERM_SUPPORT.INTERRUPT}
        self.log.debug(output.TERM_SUPPORT.MOVE_BACK + mapping[status] +
                       status + output.TERM_SUPPORT.ENDC)

    def notify_progress(self, progress=False):
        if progress:
            color = output.TERM_SUPPORT.PASS
        else:
            color = output.TERM_SUPPORT.PARTIAL
        self.log.debug(color + self.__throbber.render() +
                       output.TERM_SUPPORT.ENDC, extra={"skip_newline": True})
