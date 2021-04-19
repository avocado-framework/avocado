import glob
import os
import unittest

from avocado.core import exit_codes
from avocado.utils import process
from selftests.utils import AVOCADO, TestCaseTmpDir


class ReplayTests(TestCaseTmpDir):

    def setUp(self):
        super(ReplayTests, self).setUp()
        cmd_line = ('%s run passtest.py passtest.py passtest.py passtest.py '
                    '--job-results-dir %s --disable-sysinfo --json -'
                    % (AVOCADO, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)
        self.jobdir = ''.join(glob.glob(os.path.join(self.tmpdir.name, 'job-*')))
        idfile = ''.join(os.path.join(self.jobdir, 'id'))
        with open(idfile, 'r') as f:
            self.jobid = f.read().strip('\n')
        self.config_path = self._create_config()

    def _create_config(self):
        config_path = os.path.join(self.tmpdir.name, 'config')
        with open(config_path, 'w') as config:
            config.write("[datadir.paths]\n")
            config.write("logs_dir = %s\n" % self.tmpdir.name)
        return config_path

    def run_and_check(self, cmd_line, expected_rc):
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        return result

    def test_run_replay_noid(self):
        """
        Runs a replay job with an invalid jobid.
        """
        cmd_line = '%s --config=%s replay %s' % (AVOCADO,
                                                 self.config_path,
                                                 'foo')
        expected_rc = exit_codes.AVOCADO_FAIL
        self.run_and_check(cmd_line, expected_rc)

    def test_run_replay_latest(self):
        """
        Runs a replay job using the 'latest' keyword.
        """
        cmd_line = '%s --config=%s replay latest' % (AVOCADO,
                                                     self.config_path)
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
        cmd_line = '%s --config=%s replay %s' % (AVOCADO,
                                                 self.config_path,
                                                 self.jobdir)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)


if __name__ == '__main__':
    unittest.main()
