#!/usr/bin/env python

import unittest
import os
import sys

# simple magic for using scripts within a source tree
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
basedir = os.path.dirname(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado import sysinfo

class SysinfoTest(unittest.TestCase):

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

if __name__ == '__main__':
    unittest.main()