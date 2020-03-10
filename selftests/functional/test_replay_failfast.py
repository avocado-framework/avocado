import glob
import os
import tempfile
import unittest

from avocado.core import exit_codes
from avocado.utils import process

from .. import AVOCADO, BASEDIR, temp_dir_prefix


class ReplayFailfastTests(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)
        cmd_line = ('%s run passtest.py failtest.py passtest.py '
                    '--failfast on --job-results-dir %s --sysinfo=off --json -'
                    % (AVOCADO, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL | exit_codes.AVOCADO_JOB_INTERRUPTED
        self.run_and_check(cmd_line, expected_rc)
        self.jobdir = ''.join(glob.glob(os.path.join(self.tmpdir.name, 'job-*')))
        idfile = ''.join(os.path.join(self.jobdir, 'id'))
        with open(idfile, 'r') as f:
            self.jobid = f.read().strip('\n')

    def run_and_check(self, cmd_line, expected_rc):
        os.chdir(BASEDIR)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        return result

    def test_run_replay_failfast(self):
        cmd_line = ('%s run --replay %s --failfast on '
                    '--job-results-dir %s --sysinfo=off'
                    % (AVOCADO, self.jobid, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL | exit_codes.AVOCADO_JOB_INTERRUPTED
        self.run_and_check(cmd_line, expected_rc)

    def test_run_replay_disable_failfast(self):
        cmd_line = ('%s run --replay %s --failfast off '
                    '--job-results-dir %s --sysinfo=off'
                    % (AVOCADO, self.jobid, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        result = self.run_and_check(cmd_line, expected_rc)
        msg = (b'Overriding the replay failfast with the --failfast value '
               b'given on the command line.')
        self.assertIn(msg, result.stderr)

    def tearDown(self):
        self.tmpdir.cleanup()


if __name__ == '__main__':
    unittest.main()
