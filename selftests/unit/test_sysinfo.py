import os
import tempfile
import unittest

from avocado.core import sysinfo
from selftests.utils import temp_dir_prefix


class SysinfoTest(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    def test_loggables_equal(self):
        cmd1 = sysinfo.Command("ls -l")
        cmd2 = sysinfo.Command("ls -l")
        self.assertEqual(cmd1, cmd2)
        file1 = sysinfo.Logfile("/proc/cpuinfo")
        file2 = sysinfo.Logfile("/proc/cpuinfo")
        self.assertEqual(file1, file2)

    def test_loggables_not_equal(self):
        cmd1 = sysinfo.Command("ls -l")
        cmd2 = sysinfo.Command("ls -la")
        self.assertNotEqual(cmd1, cmd2)
        file1 = sysinfo.Logfile("/proc/cpuinfo")
        file2 = sysinfo.Logfile("/etc/fstab")
        self.assertNotEqual(file1, file2)

    def test_loggables_set(self):
        container = set()
        cmd1 = sysinfo.Command("ls -l")
        cmd2 = sysinfo.Command("ls -l")
        cmd3 = sysinfo.Command("ps -ef")
        cmd4 = sysinfo.Command("uname -a")
        file1 = sysinfo.Command("/proc/cpuinfo")
        file2 = sysinfo.Command("/etc/fstab")
        file3 = sysinfo.Command("/etc/fstab")
        file4 = sysinfo.Command("/etc/fstab")
        # From the above 8 objects, only 5 are unique loggables.
        container.add(cmd1)
        container.add(cmd2)
        container.add(cmd3)
        container.add(cmd4)
        container.add(file1)
        container.add(file2)
        container.add(file3)
        container.add(file4)

        self.assertEqual(len(container), 5)

    def test_logger_job(self):
        jobdir = os.path.join(self.tmpdir.name, 'job')
        sysinfo_logger = sysinfo.SysInfo(basedir=jobdir)
        sysinfo_logger.start()
        self.assertTrue(os.path.isdir(jobdir))
        self.assertGreaterEqual(len(os.listdir(jobdir)), 1,
                                "Job does not have 'pre' dir")
        job_predir = os.path.join(jobdir, 'pre')
        self.assertTrue(os.path.isdir(job_predir))
        sysinfo_logger.end()
        job_postdir = os.path.join(jobdir, 'post')
        self.assertTrue(os.path.isdir(job_postdir))

    def test_logger_test(self):
        testdir = os.path.join(self.tmpdir.name, 'job', 'test1')
        sysinfo_logger = sysinfo.SysInfo(basedir=testdir)
        sysinfo_logger.start()
        self.assertTrue(os.path.isdir(testdir))
        self.assertGreaterEqual(len(os.listdir(testdir)), 1,
                                "Test does not have 'pre' dir")
        test_predir = os.path.join(testdir, 'pre')
        self.assertTrue(os.path.isdir(test_predir))
        sysinfo_logger.end()
        self.assertGreaterEqual(len(os.listdir(testdir)), 2,
                                "Test does not have 'pre' dir")
        test_postdir = os.path.join(testdir, 'post')
        self.assertTrue(os.path.isdir(test_postdir))

    def tearDown(self):
        self.tmpdir.cleanup()


if __name__ == '__main__':
    unittest.main()
