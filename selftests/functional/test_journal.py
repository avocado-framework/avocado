import json
import os
import sqlite3
import unittest

from avocado.core import exit_codes
from avocado.utils import process
from selftests.utils import AVOCADO, TestCaseTmpDir


class JournalPluginTests(TestCaseTmpDir):

    def setUp(self):
        super().setUp()
        self.cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                         f'--disable-sysinfo --json - '
                         f'--journal examples/tests/passtest.py')
        self.result = process.run(self.cmd_line, ignore_status=True)
        data = json.loads(self.result.stdout_text)
        self.job_id = data['job_id']
        jfile = os.path.join(os.path.dirname(data['debuglog']), '.journal.sqlite')
        self.db = sqlite3.connect(jfile)

    def test_journal_job_id(self):
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(self.result.exit_status, expected_rc,
                         (f"Command '{self.cmd_line}' did not return "
                          f"{expected_rc}"))
        cur = self.db.cursor()
        cur.execute('SELECT unique_id FROM job_info;')
        db_job_id = cur.fetchone()[0]
        self.assertEqual(db_job_id, self.job_id,
                         (f"The job ids differs, expected {self.job_id} "
                          f"got {db_job_id}"))

    def test_journal_count_entries(self):
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(self.result.exit_status, expected_rc,
                         (f"Command '{self.cmd_line}' did not return "
                          f"{expected_rc}"))
        cur = self.db.cursor()
        cur.execute('SELECT COUNT(*) FROM test_journal;')
        db_count = cur.fetchone()[0]
        count = 2
        self.assertEqual(db_count, count,
                         (f"The checkup count of test_journal is wrong, "
                          f"expected {count} got {db_count}"))

    def tearDown(self):
        self.db.close()
        super().tearDown()


if __name__ == '__main__':
    unittest.main()
