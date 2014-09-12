#!/usr/bin/env python

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
# Author: Ruda Moura <rmoura@redhat.com>

import unittest
import os
import sys
import json
import sqlite3

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import process


class JournalPluginTests(unittest.TestCase):

    def test_journal_result(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --json - --journal examples/tests/sleeptest.py'
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, 0,
                         "Command '%s' did not return 0" % cmd_line)
        data = json.loads(result.stdout)
        job_id = data['job_id']
        jfile = os.path.join(os.path.dirname(data['debuglog']),
                             'test-results/examples/tests/.journal.sqlite')
        print jfile
        db = sqlite3.connect(jfile)
        cur = db.cursor()
        cur.execute('SELECT unique_id FROM job_info;')
        db_job_id = cur.fetchone()[0]
        self.assertEqual(db_job_id, job_id,
                         "The job ids differs, expected %s got %s" % (job_id, db_job_id))
        cur.execute('SELECT COUNT(*) FROM test_journal;')
        db_count = cur.fetchone()[0]
        count = 2
        self.assertEqual(db_count, count,
                         "The checkup count of test_journal is wrong, expected %d got %d" % (count, db_count))

if __name__ == '__main__':
    unittest.main()
