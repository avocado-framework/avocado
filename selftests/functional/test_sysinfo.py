import os
import sys
import shutil
import tempfile

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.utils import process


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


class SysInfoTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_sysinfo_enabled(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --job-results-dir %s --sysinfo=on passtest' % self.tmpdir
        result = process.run(cmd_line)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc %d:\n%s' % (expected_rc, result))
        output = result.stdout + result.stderr
        for line in output.splitlines():
            if 'JOB LOG' in line:
                job_log = line.split()[-1]
                sysinfo_dir = os.path.join(os.path.dirname(job_log), 'sysinfo')
        msg = "Avocado didn't create sysinfo directory %s:\n%s" % (sysinfo_dir, result)
        self.assertTrue(os.path.isdir(sysinfo_dir), msg)
        msg = 'The sysinfo directory is empty:\n%s' % result
        self.assertGreater(len(os.listdir(sysinfo_dir)), 0, msg)
        for hook in ('pre', 'post'):
            sysinfo_subdir = os.path.join(sysinfo_dir, hook)
            msg = 'The sysinfo/%s subdirectory does not exist:\n%s' % (hook, result)
            self.assertTrue(os.path.exists(sysinfo_subdir), msg)

    def test_sysinfo_disabled(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --job-results-dir %s --sysinfo=off passtest' % self.tmpdir
        result = process.run(cmd_line)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc %d:\n%s' % (expected_rc, result))
        output = result.stdout + result.stderr
        for line in output.splitlines():
            if 'JOB LOG' in line:
                job_log = line.split()[-1]
                sysinfo_dir = os.path.join(os.path.dirname(job_log), 'sysinfo')
        msg = 'Avocado created sysinfo directory %s:\n%s' % (sysinfo_dir, result)
        self.assertFalse(os.path.isdir(sysinfo_dir), msg)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

if __name__ == '__main__':
    unittest.main()
