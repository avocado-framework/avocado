#!/usr/bin/env python

import os
import sys
import unittest
import tempfile

# simple magic for using scripts within a source tree
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
basedir = os.path.dirname(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado import sysinfo


class SysinfoTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="sysinfo_unittest")

    def testLoggablesEqual(self):
        cmd1 = sysinfo.Command("ls -l")
        cmd2 = sysinfo.Command("ls -l")
        self.assertEqual(cmd1, cmd2)
        file1 = sysinfo.Logfile("/proc/cpuinfo")
        file2 = sysinfo.Logfile("/proc/cpuinfo")
        self.assertEqual(file1, file2)

    def testLoggablesNotEqual(self):
        cmd1 = sysinfo.Command("ls -l")
        cmd2 = sysinfo.Command("ls -la")
        self.assertNotEqual(cmd1, cmd2)
        file1 = sysinfo.Logfile("/proc/cpuinfo")
        file2 = sysinfo.Logfile("/etc/fstab")
        self.assertNotEqual(file1, file2)

    def testLoggablesSet(self):
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

    def test_logger_job_hooks(self):
        jobdir = os.path.join(self.tmpdir, 'job')
        sysinfo_logger = sysinfo.SysInfo(basedir=jobdir)
        sysinfo_logger.start_job_hook()
        self.assertTrue(os.path.isdir(jobdir))
        self.assertEqual(len(os.listdir(jobdir)), 1,
                         "Job does not have 'pre' dir")
        job_predir = os.path.join(jobdir, 'pre')
        self.assertTrue(os.path.isdir(job_predir))
        self.assertGreater(len(os.listdir(job_predir)), 0,
                           "Job pre dir is empty")
        sysinfo_logger.end_job_hook()
        job_postdir = os.path.join(jobdir, 'post')
        self.assertTrue(os.path.isdir(job_postdir))
        self.assertGreater(len(os.listdir(job_postdir)), 0,
                           "Job post dir is empty")

    def test_logger_test_hooks(self):
        testdir = os.path.join(self.tmpdir, 'job', 'test1')
        sysinfo_logger = sysinfo.SysInfo(basedir=testdir)
        sysinfo_logger.start_test_hook()
        self.assertTrue(os.path.isdir(testdir))
        self.assertEqual(len(os.listdir(testdir)), 1,
                         "Test does not have 'pre' dir")
        test_predir = os.path.join(testdir, 'pre')
        self.assertTrue(os.path.isdir(test_predir))
        # By default, there are no pre test files
        self.assertEqual(len(os.listdir(test_predir)), 0,
                         "Test pre dir is not empty")
        sysinfo_logger.end_test_hook()
        self.assertEqual(len(os.listdir(testdir)), 2,
                         "Test does not have 'pre' dir")
        job_postdir = os.path.join(testdir, 'post')
        self.assertTrue(os.path.isdir(job_postdir))
        # By default, there are no post test files
        self.assertEqual(len(os.listdir(job_postdir)), 0,
                         "Test post dir is not empty")

    def tearDown(self):
        try:
            os.rmdir(self.tmpdir)
        except OSError:
            pass

if __name__ == '__main__':
    unittest.main()
