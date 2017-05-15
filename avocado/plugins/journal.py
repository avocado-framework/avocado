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

from avocado.core.plugin_interfaces import CLI, ResultEvents

JOURNAL_FILENAME = ".journal.sqlite"

SCHEMA = {'job_info': 'CREATE TABLE job_info (unique_id TEXT UNIQUE)',
          'test_journal': ("CREATE TABLE test_journal ("
                           "tag TEXT, "
                           "time TEXT, "
                           "action TEXT, "
                           "status TEXT, "
                           "flushed BOOLEAN DEFAULT 0)")}


class JournalResult(ResultEvents):

    """
    Test Result Journal class.

    This class keeps a log of the test updates: started running, finished, etc.
    This information can be forwarded live to an avocado server and provide
    feedback to users from a central place.
    """

    name = 'journal'
    description = "Journal event based results implementation"

    def __init__(self, args):
        """
        Creates an instance of ResultJournal.

        :param job: an instance of :class:`avocado.core.job.Job`.
        """
        self.journal_initialized = False

    def _init_journal(self, logdir):
        self.journal_path = os.path.join(logdir, JOURNAL_FILENAME)
        self.journal = sqlite3.connect(self.journal_path)
        self.journal_cursor = self.journal.cursor()
        for table in SCHEMA:
            res = self.journal_cursor.execute("PRAGMA table_info('%s')" % table)
            if res.fetchone() is None:
                self.journal_cursor.execute(SCHEMA[table])
        self.journal.commit()

    def lazy_init_journal(self, state):
        # lazy init because we need the toplevel logdir for the job
        if not self.journal_initialized:
            self._init_journal(state['job_logdir'])
            self._record_job_info(state)
            self.journal_initialized = True

    def _shutdown_journal(self):
        if self.journal_initialized:
            self.journal.close()

    def _record_job_info(self, state):
        res = self.journal_cursor.execute("SELECT unique_id FROM job_info")
        if res.fetchone() is None:
            sql = "INSERT INTO job_info (unique_id) VALUES (?)"
            self.journal_cursor.execute(sql, (state['job_unique_id'], ))
            self.journal.commit()

    def _record_status(self, state, action):
        sql = "INSERT INTO test_journal (tag, time, action, status) VALUES (?, ?, ?, ?)"

        # This shouldn't be required
        if action == "ENDED":
            status = state['status']
        else:
            status = None

        self.journal_cursor.execute(sql,
                                    (repr(state['name']),
                                     datetime.datetime(1, 1, 1).now().isoformat(),
                                     action,
                                     status))
        self.journal.commit()

    def pre_tests(self, job):
        pass

    def start_test(self, result, state):
        self.lazy_init_journal(state)
        self._record_status(state, "STARTED")

    def test_progress(self, progress=False):
        pass

    def end_test(self, result, state):
        self.lazy_init_journal(state)
        self._record_status(state, "ENDED")

    def post_tests(self, job):
        self._shutdown_journal()


class Journal(CLI):

    """
    Test journal
    """

    name = 'journal'
    description = "Journal options for the 'run' subcommand"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        self.parser = parser
        help_msg = ('Records test status changes (for use with '
                    'avocado-journal-replay and avocado-server)')
        run_subcommand_parser.output.add_argument('--journal',
                                                  action='store_true',
                                                  help=help_msg)

    def run(self, args):
        pass
