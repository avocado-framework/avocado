import glob
import os
import tempfile
import shutil
import unittest

from avocado.core import exit_codes
from avocado.utils import process


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)

AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD", "./scripts/avocado")


class ReplayFailfastTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        cmd_line = ('%s run passtest.py failtest.py passtest.py '
                    '--failfast on --job-results-dir %s --sysinfo=off --json -'
                    % (AVOCADO, self.tmpdir))
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL | exit_codes.AVOCADO_JOB_INTERRUPTED
        self.run_and_check(cmd_line, expected_rc)
        self.jobdir = ''.join(glob.glob(os.path.join(self.tmpdir, 'job-*')))
        idfile = ''.join(os.path.join(self.jobdir, 'id'))
        with open(idfile, 'r') as f:
            self.jobid = f.read().strip('\n')

    def run_and_check(self, cmd_line, expected_rc):
        os.chdir(basedir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        return result

    def test_run_replay_failfast(self):
        cmd_line = ('%s run --replay %s '
                    '--job-results-dir %s --sysinfo=off'
                    % (AVOCADO, self.jobid, self.tmpdir))
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL | exit_codes.AVOCADO_JOB_INTERRUPTED
        result = self.run_and_check(cmd_line, expected_rc)

    def test_run_replay_disable_failfast(self):
        cmd_line = ('%s run --replay %s --failfast off '
                    '--job-results-dir %s --sysinfo=off'
                    % (AVOCADO, self.jobid, self.tmpdir))
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        result = self.run_and_check(cmd_line, expected_rc)
        msg = 'Overriding the replay failfast with the --failfast value given on the command line.'
        self.assertIn(msg, result.stderr)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
