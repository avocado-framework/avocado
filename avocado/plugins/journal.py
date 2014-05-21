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
# Copyright: Red Hat Inc. 2014
# Author: Cleber Rosa <cleber@redhat.com>

"""Journal Plugin"""

import os
import sqlite3
import datetime

from avocado.plugins import plugin
from avocado.result import TestResult

JOURNAL_FILENAME = ".journal.sqlite"

JOB_INFO_SCHEMA = ("CREATE TABLE job_info ("
                   "unique_id TEXT)")

TEST_JOURNAL_SCHEMA = ("CREATE TABLE test_journal ("
                       "tag TEXT, "
                       "time TEXT, "
                       "action TEXT, "
                       "status TEXT, "
                       "flushed BOOLEAN DEFAULT 0)")


class TestResultJournal(TestResult):

    """
    Test Result Journal class.

    This class keeps a log of the test updates: started running, finished, etc.
    This information can be forwarded live to an avocado server and provide
    feedback to users from a central place.
    """

    def __init__(self, stream=None, args=None):
        """
        Creates an instance of TestResultJournal.

        :param stream: an instance of :class:`avocado.core.output.OutputManager`.
        :param args: an instance of :class:`argparse.Namespace`.
        """
        TestResult.__init__(self, stream, args)
        self.journal_initialized = False

    def _init_journal(self, logdir):
        self.journal_path = os.path.join(logdir, JOURNAL_FILENAME)
        self.journal = sqlite3.connect(self.journal_path)
        self.journal_cursor = self.journal.cursor()
        self.journal_cursor.execute(JOB_INFO_SCHEMA)
        self.journal_cursor.execute(TEST_JOURNAL_SCHEMA)
        self.journal.commit()

    def _shutdown_journal(self):
        self.journal.close()

    def _record_job_info(self, test):
        sql = "INSERT INTO job_info (unique_id) VALUES (?)"
        self.journal_cursor.execute(sql, (test.job.unique_id, ))
        self.journal.commit()

    def _record_status(self, test, action):
        sql = "INSERT INTO test_journal (tag, time, action, status) VALUES (?, ?, ?, ?)"

        # This shouldn't be required
        if action == "ENDED":
            status = test.status
        else:
            status = None

        self.journal_cursor.execute(sql,
                                    (test.tagged_name,
                                     datetime.datetime(1, 1, 1).now().isoformat(),
                                     action,
                                     status))
        self.journal.commit()

    def start_test(self, test):
        # lazy init because we need the toplevel logdir for the job
        if not self.journal_initialized:
            self._init_journal(os.path.dirname(test.logdir))
            self._record_job_info(test)
            self.journal_initialized = True

        TestResult.start_test(self, test)
        self._record_status(test, "STARTED")

    def end_test(self, test):
        TestResult.end_test(self, test)
        self._record_status(test, "ENDED")

    def end_tests(self):
        self._shutdown_journal()


class Journal(plugin.Plugin):

    """
    Test journal plugin
    """

    name = 'journal'
    enabled = True

    def configure(self, app_parser, cmd_parser):
        self.parser = app_parser
        app_parser.add_argument('--journal', action='store_true',
                                help='Records test status changes')
        self.configured = True

    def activate(self, app_args):
        if app_args.journal:
            self.parser.set_defaults(test_result=TestResultJournal)
