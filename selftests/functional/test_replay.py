import glob
import os
import unittest

from avocado.core import exit_codes
from avocado.utils import process
from selftests.utils import AVOCADO, TestCaseTmpDir


class ReplayTests(TestCaseTmpDir):

    def setUp(self):
        super().setUp()
        cmd_line = (f'{AVOCADO} run examples/tests/passtest.py '
                    f'examples/tests/passtest.py '
                    f'examples/tests/passtest.py '
                    f'examples/tests/passtest.py '
                    f'--job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo --json -')
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)
        self.jobdir = ''.join(glob.glob(os.path.join(self.tmpdir.name, 'job-*')))
        idfile = ''.join(os.path.join(self.jobdir, 'id'))
        with open(idfile, 'r', encoding='utf-8') as f:
            self.jobid = f.read().strip('\n')
        self.config_path = self._create_config()

    def _create_config(self):
        config_path = os.path.join(self.tmpdir.name, 'config')
        with open(config_path, 'w', encoding='utf-8') as config:
            config.write("[datadir.paths]\n")
            config.write(f"logs_dir = {self.tmpdir.name}\n")
        return config_path

    def run_and_check(self, cmd_line, expected_rc):
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         (f"Command {cmd_line} did not return rc "
                          f"{expected_rc}:\n{result}"))
        return result

    def test_run_replay_noid(self):
        """
        Runs a replay job with an invalid jobid.
        """
        cmd_line = f"{AVOCADO} --config={self.config_path} replay {'foo'}"
        expected_rc = exit_codes.AVOCADO_FAIL
        self.run_and_check(cmd_line, expected_rc)

    def test_run_replay_latest(self):
        """
        Runs a replay job using the 'latest' keyword.
        """
        cmd_line = f'{AVOCADO} --config={self.config_path} replay latest'
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)

    def test_run_replay_data(self):
        """
        Checks if all expected files are there.
        """
        file_list = ['variants-1.json', 'config', 'test_references', 'pwd',
                     'args.json', 'cmdline']
        for filename in file_list:
            path = os.path.join(self.jobdir, 'jobdata', filename)
            self.assertTrue(glob.glob(path))

    def test_run_replay(self):
        """
        Runs a replay job.
        """
        cmd_line = (f'{AVOCADO} --config={self.config_path} '
                    f'replay {self.jobdir}')
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)


if __name__ == '__main__':
    unittest.main()
