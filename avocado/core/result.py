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
Contains the definition of the Result class, used for output in avocado.
"""
from . import dispatcher
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
    :type klass: a subclass of :class:`Result`
    """
    if not hasattr(application_args, 'test_result_classes'):
        application_args.test_result_classes = set()
    application_args.test_result_classes.add(klass)


class ResultProxy(object):

    def __init__(self):
        self.output_plugins = []

    def notify_progress(self, progress_from_test=False):
        for output_plugin in self.output_plugins:
            if hasattr(output_plugin, 'notify_progress'):
                output_plugin.notify_progress(progress_from_test)

    def add_output_plugin(self, plugin):
        if not isinstance(plugin, Result):
            raise InvalidOutputPlugin("Object %s is not an instance of "
                                      "Result" % plugin)
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

    def check_test(self, state):
        for output_plugin in self.output_plugins:
            output_plugin.check_test(state)

    def set_tests_total(self, tests_total):
        for output_plugin in self.output_plugins:
            output_plugin.tests_total = tests_total


class Result(object):

    """
    Result class, holder for job (and its tests) result information.
    """

    def __init__(self, job):
        """
        Creates an instance of Result.

        :param job: an instance of :class:`avocado.core.job.Job`.
        """
        self.job_unique_id = getattr(job, "unique_id")
        self.logfile = getattr(job, "logfile", None)
        self.tests_total = 0
        self.tests_run = 0
        self.tests_total_time = 0.0
        self.passed = 0
        self.errors = 0
        self.failed = 0
        self.skipped = 0
        self.warned = 0
        self.interrupted = 0
        self.tests = []
        self._result_events_dispatcher = dispatcher.ResultEventsDispatcher(job.args)
        output.log_plugin_failures(self._result_events_dispatcher.load_failures)
        self.job = job

    def _reconcile(self):
        """
        Make sure job results are reconciled

        In situations such as job interruptions, some test results will be
        missing, but this is no excuse for giving wrong summaries of test
        results.
        """
        valid_results_count = (self.passed + self.errors +
                               self.failed + self.warned +
                               self.skipped + self.interrupted)
        other_skipped_count = self.tests_total - valid_results_count
        if other_skipped_count > 0:
            self.skipped += other_skipped_count
        else:
            self.tests_total -= other_skipped_count

    def start_tests(self):
        """
        Called once before any tests are executed.
        """
        self.tests_run += 1
        self._result_events_dispatcher.map_method('pre_tests', self.job)

    def end_tests(self):
        """
        Called once after all tests are executed.
        """
        self._reconcile()
        self._result_events_dispatcher.map_method('post_tests', self.job)

    def start_test(self, state):
        """
        Called when the given test is about to run.

        :param state: result of :class:`avocado.core.test.Test.get_state`.
        :type state: dict
        """
        self._result_events_dispatcher.map_method('start_test', self, state)

    def end_test(self, state):
        """
        Called when the given test has been run.

        :param state: result of :class:`avocado.core.test.Test.get_state`.
        :type state: dict
        """
        self.tests_run += 1
        self.tests_total_time += state.get('time_elapsed', -1)
        self.tests.append(state)
        self._result_events_dispatcher.map_method('end_test', self, state)

    def check_test(self, state):
        """
        Called once for a test to check status and report.

        :param test: A dict with test internal state
        """
        status = state.get('status')
        if status == "PASS":
            self.passed += 1
        elif status == "SKIP":
            self.skipped += 1
        elif status == "FAIL":
            self.failed += 1
        elif status == "WARN":
            self.warned += 1
        elif status == "INTERRUPTED":
            self.interrupted += 1
        else:
            self.errors += 1
        self.end_test(state)

    def notify_progress(self, progress=False):
        """
        Notify the progress of the test

        :param progress: True means there is progress, False means test stall
        """
        self._result_events_dispatcher.map_method('test_progress', progress)
