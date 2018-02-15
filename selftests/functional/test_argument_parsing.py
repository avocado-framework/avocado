import os
import glob
import unittest

from avocado.core import data_dir
from avocado.core import job_id
from avocado.core import exit_codes
from avocado.utils import process


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)

AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD", "./scripts/avocado")


class ArgumentParsingTest(unittest.TestCase):

    def test_unknown_command(self):
        os.chdir(basedir)
        cmd_line = '%s whacky-command-that-doesnt-exist' % AVOCADO
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc %d:\n%s' % (expected_rc, result))

    def test_known_command_bad_choice(self):
        os.chdir(basedir)
        cmd_line = '%s run --sysinfo=foo passtest' % AVOCADO
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc %d:\n%s' % (expected_rc, result))

    def test_known_command_bad_argument(self):
        os.chdir(basedir)
        cmd_line = '%s run --sysinfo=off --whacky-argument passtest' % AVOCADO
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc %d:\n%s' % (expected_rc, result))
        subcommand_error_msg = (b'avocado run: error: unrecognized arguments: '
                                b'--whacky-argument')
        self.assertIn(subcommand_error_msg, result.stderr)


class ArgumentParsingErrorEarlyTest(unittest.TestCase):

    def run_but_fail_before_create_job_dir(self, complement_args, expected_rc):
        """
        Runs avocado but checks that it fails before creating the job dir

        :param complement_args: the complement arguments to an 'avocado run'
                                command line
        """
        os.chdir(basedir)
        log_dir = data_dir.get_logs_dir()
        self.assertIsNotNone(log_dir)
        job = job_id.create_unique_job_id()
        cmd_line = '%s run --sysinfo=off --force-job-id=%%s %%s' % AVOCADO
        cmd_line %= (job, complement_args)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc %d:\n%s' % (expected_rc, result))
        path_job_glob = os.path.join(log_dir, "job-*-%s" % job[0:7])
        self.assertEqual(glob.glob(path_job_glob), [])

    def test_whacky_option(self):
        self.run_but_fail_before_create_job_dir('--whacky-option passtest',
                                                exit_codes.AVOCADO_FAIL)


if __name__ == '__main__':
    unittest.main()
