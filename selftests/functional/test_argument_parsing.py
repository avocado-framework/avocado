import glob
import os
import unittest

from avocado.core import exit_codes, job_id
from avocado.core.settings import settings
from avocado.utils import process
from selftests.utils import AVOCADO, BASEDIR


class ArgumentParsingTest(unittest.TestCase):

    def test_unknown_command(self):
        os.chdir(BASEDIR)
        cmd_line = f'{AVOCADO} whacky-command-that-doesnt-exist'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc {expected_rc}:\n{result}')

    def test_known_command_bad_choice(self):
        os.chdir(BASEDIR)
        cmd_line = f'{AVOCADO} run --disable-sysinfo=foo passtest'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc {expected_rc}:\n{result}')

    def test_known_command_bad_argument(self):
        os.chdir(BASEDIR)
        cmd_line = f'{AVOCADO} run --disable-sysinfo --whacky-argument passtest'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc {expected_rc}:\n{result}')
        subcommand_error_msg = (b'avocado run: error: unrecognized arguments: '
                                b'--whacky-argument')
        self.assertIn(subcommand_error_msg, result.stderr)
        self.assertIn(b"run 'avocado plugins'", result.stderr)


class ArgumentParsingErrorEarlyTest(unittest.TestCase):

    def run_but_fail_before_create_job_dir(self, complement_args, expected_rc):
        """
        Runs avocado but checks that it fails before creating the job dir

        :param complement_args: the complement arguments to an 'avocado run'
                                command line
        """
        os.chdir(BASEDIR)
        config = settings.as_dict()
        log_dir = config.get('datadir.paths.logs_dir')

        self.assertIsNotNone(log_dir)
        job = job_id.create_unique_job_id()
        cmd_line = (f'{AVOCADO} run --disable-sysinfo '
                    f'--force-job-id={job} {complement_args}')
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc {expected_rc}:\n{result}')
        path_job_glob = os.path.join(log_dir, f"job-*-{job[0:7]}")
        self.assertEqual(glob.glob(path_job_glob), [])

    def test_whacky_option(self):
        self.run_but_fail_before_create_job_dir('--whacky-option passtest',
                                                exit_codes.AVOCADO_FAIL)


if __name__ == '__main__':
    unittest.main()
