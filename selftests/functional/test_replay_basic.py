import glob
import os
import tempfile
import unittest

from avocado.core import exit_codes
from avocado.utils import process

from .. import AVOCADO, BASEDIR, temp_dir_prefix


class ReplayTests(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)
        cmd_line = ('%s run passtest.py passtest.py passtest.py passtest.py '
                    '--job-results-dir %s --sysinfo=off --json -'
                    % (AVOCADO, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
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

    def test_run_replay_noid(self):
        """
        Runs a replay job with an invalid jobid.
        """
        cmd_line = ('%s run --replay %s '
                    '--job-results-dir %s --sysinfo=off'
                    % (AVOCADO, 'foo', self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_FAIL
        self.run_and_check(cmd_line, expected_rc)

    def test_run_replay_latest(self):
        """
        Runs a replay job using the 'latest' keyword.
        """
        cmd_line = ('%s run --replay latest --job-results-dir %s --sysinfo=off'
                    % (AVOCADO, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)

    def test_run_replay_data(self):
        """
        Checks if all expected files are there.
        """
        file_list = ['variants.json', 'config', 'test_references', 'pwd',
                     'args.json', 'cmdline']
        for filename in file_list:
            path = os.path.join(self.jobdir, 'jobdata', filename)
            self.assertTrue(glob.glob(path))

    def test_run_replay(self):
        """
        Runs a replay job.
        """
        cmd_line = ('%s run --replay %s '
                    '--job-results-dir %s --sysinfo=off'
                    % (AVOCADO, self.jobid, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)

    def test_run_replay_partialid(self):
        """
        Runs a replay job with a partial jobid.
        """
        partial_id = self.jobid[:5]
        cmd_line = ('%s run --replay %s '
                    '--job-results-dir %s --sysinfo=off'
                    % (AVOCADO, partial_id, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)

    def test_run_replay_results_as_jobid(self):
        """
        Runs a replay job identifying the job by its results directory.
        """
        cmd_line = ('%s run --replay %s '
                    '--job-results-dir %s --sysinfo=off'
                    % (AVOCADO, self.jobdir, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)

    def test_run_replay_invalidignore(self):
        """
        Runs a replay job with an invalid option for '--replay-ignore'
        """
        cmd_line = ('%s run --replay %s --replay-ignore foo'
                    '--job-results-dir %s --sysinfo=off'
                    % (AVOCADO, self.jobid, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_FAIL
        result = self.run_and_check(cmd_line, expected_rc)
        msg = (b'Invalid --replay-ignore option. Valid options are '
               b'(more than one allowed): variants,config')
        self.assertIn(msg, result.stderr)

    def test_run_replay_ignorevariants(self):
        """
        Runs a replay job ignoring the variants.
        """
        cmd_line = ('%s run --replay %s --replay-ignore variants '
                    '--job-results-dir %s --sysinfo=off'
                    % (AVOCADO, self.jobid, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        result = self.run_and_check(cmd_line, expected_rc)
        msg = b'Ignoring variants from source job with --replay-ignore.'
        self.assertIn(msg, result.stderr)

    def test_run_replay_invalidstatus(self):
        """
        Runs a replay job with an invalid option for '--replay-test-status'
        """
        cmd_line = ('%s run --replay %s --replay-test-status E '
                    '--job-results-dir %s --sysinfo=off'
                    % (AVOCADO, self.jobid, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_FAIL
        result = self.run_and_check(cmd_line, expected_rc)
        msg = (b'Invalid --replay-test-status option. Valid options are (more '
               b'than one allowed): SKIP,ERROR,FAIL,WARN,PASS,INTERRUPTED')
        self.assertIn(msg, result.stderr)

    def test_run_replay_statusfail(self):
        """
        Runs a replay job only with tests that failed.
        """
        cmd_line = ('%s run --replay %s --replay-test-status '
                    'FAIL --job-results-dir %s --sysinfo=off'
                    % (AVOCADO, self.jobid, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        result = self.run_and_check(cmd_line, expected_rc)
        msg = (b'RESULTS    : PASS 0 | ERROR 0 | FAIL 0 | SKIP 4 | WARN 0 | '
               b'INTERRUPT 0')
        self.assertIn(msg, result.stdout)

    def test_run_replay_status_and_variants(self):
        """
        Runs a replay job with custom variants using '--replay-test-status'
        """
        cmd_line = ('%s run --replay %s --replay-ignore variants '
                    '--replay-test-status FAIL --job-results-dir %s '
                    '--sysinfo=off' % (AVOCADO, self.jobid, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_FAIL
        result = self.run_and_check(cmd_line, expected_rc)
        msg = (b"Option `--replay-test-status` is incompatible with "
               b"`--replay-ignore variants`")
        self.assertIn(msg, result.stderr)

    def test_run_replay_status_and_references(self):
        """
        Runs a replay job with custom test references and --replay-test-status
        """
        cmd_line = ('%s run sleeptest --replay %s '
                    '--replay-test-status FAIL --job-results-dir %s '
                    '--sysinfo=off' % (AVOCADO, self.jobid, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_FAIL
        result = self.run_and_check(cmd_line, expected_rc)
        msg = (b"Option --replay-test-status is incompatible with "
               b"test references given on the command line.")
        self.assertIn(msg, result.stderr)

    def tearDown(self):
        self.tmpdir.cleanup()


if __name__ == '__main__':
    unittest.main()
