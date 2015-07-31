import os
import sys
import glob

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.insert(0, basedir)

from avocado.core import data_dir
from avocado.core import job_id
from avocado.utils import process


class ArgumentParsingTest(unittest.TestCase):

    def test_unknown_command(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado whacky-command-that-doesnt-exist'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 2
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc %d:\n%s' % (expected_rc, result))

    def test_known_command_bad_choice(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=foo passtest'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 2
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc %d:\n%s' % (expected_rc, result))

    def test_known_command_bad_argument(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off --whacky-argument passtest'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 2
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc %d:\n%s' % (expected_rc, result))


class ArgumentParsingErrorEarlyTest(unittest.TestCase):

    def run_but_fail_before_create_job_dir(self, complement_args):
        """
        Runs avocado but checks that it fails before creating the job dir

        :param complement_args: the complement arguments to an 'avocado run'
                                command line
        """
        os.chdir(basedir)
        log_dir = data_dir.get_logs_dir()
        self.assertIsNotNone(log_dir)
        job = job_id.create_unique_job_id()
        cmd_line = './scripts/avocado run --sysinfo=off --force-job-id=%s %s'
        cmd_line %= (job, complement_args)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 2
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc %d:\n%s' % (expected_rc, result))
        path_job_glob = os.path.join(log_dir, "job-*-%s" % job[0:7])
        self.assertEquals(glob.glob(path_job_glob), [])

    def test_whacky_option(self):
        self.run_but_fail_before_create_job_dir('--whacky-option passtest')

    def test_empty_option(self):
        self.run_but_fail_before_create_job_dir('')

if __name__ == '__main__':
    unittest.main()
