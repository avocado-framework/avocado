import os
import json
import sqlite3
import tempfile
import unittest

from avocado.core import exit_codes
from avocado.utils import process

from .. import AVOCADO, BASEDIR, temp_dir_prefix


class JournalPluginTests(unittest.TestCase):

    def setUp(self):
        os.chdir(BASEDIR)
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)
        self.cmd_line = ('%s run --job-results-dir %s --sysinfo=off --json - '
                         '--journal examples/tests/passtest.py'
                         % (AVOCADO, self.tmpdir.name))
        self.result = process.run(self.cmd_line, ignore_status=True)
        data = json.loads(self.result.stdout_text)
        self.job_id = data['job_id']
        jfile = os.path.join(os.path.dirname(data['debuglog']), '.journal.sqlite')
        self.db = sqlite3.connect(jfile)

    def test_journal_job_id(self):
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(self.result.exit_status, expected_rc,
                         "Command '%s' did not return %s" % (self.cmd_line,
                                                             expected_rc))
        cur = self.db.cursor()
        cur.execute('SELECT unique_id FROM job_info;')
        db_job_id = cur.fetchone()[0]
        self.assertEqual(db_job_id, self.job_id,
                         "The job ids differs, expected %s got %s" % (self.job_id, db_job_id))

    def test_journal_count_entries(self):
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(self.result.exit_status, expected_rc,
                         "Command '%s' did not return %s" % (self.cmd_line,
                                                             expected_rc))
        cur = self.db.cursor()
        cur.execute('SELECT COUNT(*) FROM test_journal;')
        db_count = cur.fetchone()[0]
        count = 2
        self.assertEqual(db_count, count,
                         "The checkup count of test_journal is wrong, expected %d got %d" % (count, db_count))

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()


if __name__ == '__main__':
    unittest.main()
