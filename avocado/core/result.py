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
Contains the Result class, used for result accounting.
"""


class Result:

    """
    Result class, holder for job (and its tests) result information.
    """

    def __init__(self, job_unique_id, job_logfile):
        """
        Creates an instance of Result.

        :param job_unique_id: the job's unique ID, usually from
                              :attr:`avocado.core.job.Job.unique_id`
        :param job_logfile: the job's unique ID, usually from
                            :attr:`avocado.core.job.Job.logfile`
        """
        self.job_unique_id = job_unique_id
        self.logfile = job_logfile
        self.tests_total = 0
        self.tests_run = 0
        self.tests_total_time = 0.0
        self.passed = 0
        self.errors = 0
        self.failed = 0
        self.skipped = 0
        self.warned = 0
        self.interrupted = 0
        self.cancelled = 0
        self.tests = []

    def _reconcile(self):
        """
        Make sure job results are reconciled

        In situations such as job interruptions, some test results will be
        missing, but this is no excuse for giving wrong summaries of test
        results.
        """
        valid_results_count = (self.passed + self.errors +
                               self.failed + self.warned +
                               self.skipped + self.interrupted +
                               self.cancelled)
        other_skipped_count = self.tests_total - valid_results_count
        if other_skipped_count > 0:
            self.skipped += other_skipped_count
        else:
            self.tests_total -= other_skipped_count

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

    def end_test(self, state):
        """
        Called when the given test has been run.

        :param state: result of :class:`avocado.core.test.Test.get_state`.
        :type state: dict
        """
        self.tests_run += 1
        self.tests_total_time += state.get('time_elapsed', -1)
        self.tests.append(state)

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
        elif status == "CANCEL":
            self.cancelled += 1
        else:
            self.errors += 1
        self.end_test(state)

    @property
    def rate(self):
        total = float(self.tests_total - self.skipped - self.cancelled)
        if not total:
            return 0.0
        succeeded = float(self.passed + self.warned)
        return 100 * (succeeded / total)
