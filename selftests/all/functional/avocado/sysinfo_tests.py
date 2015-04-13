import os
import sys

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import process


class SysInfoTest(unittest.TestCase):

    def test_sysinfo_enabled(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=on passtest'
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
        cmd_line = './scripts/avocado run --sysinfo=off passtest'
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


if __name__ == '__main__':
    unittest.main()
