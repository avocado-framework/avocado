"""
avocado.utils.partition unittests
:author: Lukas Doktor <ldoktor@redhat.com>
:copyright: 2016 Red Hat, Inc
"""

import os
import shutil
import sys
import tempfile
import time

from flexmock import flexmock, flexmock_teardown

from avocado.utils import partition, process
from avocado.utils import path as utils_path

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest    # pylint: disable=E0401
else:
    import unittest     # pylint: disable=C0411


def missing_binary(binary):
    try:
        utils_path.find_command(binary)
        return False
    except utils_path.CmdNotFoundError:
        return True


def cannot_sudo(command):
    try:
        process.run(command, sudo=True)
        False
    except (process.CmdError, OSError):
        return True


class TestPartition(unittest.TestCase):

    """
    Unit tests for avocado.utils.partition
    """

    @unittest.skipIf(missing_binary('mkfs.ext2'),
                     "mkfs.ext2 is required for these tests to run.")
    @unittest.skipIf(missing_binary('sudo'),
                     "sudo is required for these tests to run.")
    @unittest.skipIf(cannot_sudo('mount'),
                     'current user must be allowed to run "mount" under sudo')
    @unittest.skipIf(cannot_sudo('mkfs.ext2 -V'),
                     'current user must be allowed to run "mkfs.ext2" under sudo')
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="avocado_" + __name__)
        self.mountpoint = os.path.join(self.tmpdir, "disk")
        os.mkdir(self.mountpoint)
        self.disk = partition.Partition(os.path.join(self.tmpdir, "block"), 1,
                                        self.mountpoint)

    def test_basic(self):
        """ Test the basic workflow """
        self.assertEqual(None, self.disk.get_mountpoint())
        self.disk.mkfs()
        self.disk.mount()
        self.assertIn(self.mountpoint, open("/proc/mounts").read())
        self.assertEqual(self.mountpoint, self.disk.get_mountpoint())
        self.disk.unmount()
        self.assertNotIn(self.mountpoint, open("/proc/mounts").read())

    def test_force_unmount(self):
        """ Test force-unmount feature """
        self.disk.mkfs()
        self.disk.mount()
        self.assertIn(self.mountpoint, open("/proc/mounts").read())
        proc = process.SubProcess("cd %s; while :; do echo a > a; rm a; done"
                                  % self.mountpoint, shell=True)
        proc.start()
        self.assertTrue(self.disk.unmount())
        self.assertEqual(proc.poll(), -9)   # Process should be killed -9
        self.assertNotIn(self.mountpoint, open("/proc/mounts").read())

    def test_double_mount(self):
        """ Check the attempt for second mount fails """
        self.disk.mkfs()
        self.disk.mount()
        self.assertIn(self.mountpoint, open("/proc/mounts").read())
        self.assertRaises(partition.PartitionError, self.disk.mount)
        self.assertIn(self.mountpoint, open("/proc/mounts").read())

    def test_double_umount(self):
        """ Check double unmount works well """
        self.disk.mkfs()
        self.disk.mount()
        self.assertIn(self.mountpoint, open("/proc/mounts").read())
        self.disk.unmount()
        self.assertNotIn(self.mountpoint, open("/proc/mounts").read())
        self.disk.unmount()
        self.assertNotIn(self.mountpoint, open("/proc/mounts").read())

    def test_format_mounted(self):
        """ Check format on mounted device fails """
        self.disk.mkfs()
        self.disk.mount()
        self.assertIn(self.mountpoint, open("/proc/mounts").read())
        self.assertRaises(partition.PartitionError, self.disk.mkfs)

    def tearDown(self):
        self.disk.unmount()
        shutil.rmtree(self.tmpdir)


class TestMtabLock(unittest.TestCase):

    """
    Unit tests for avocado.utils.partition
    """

    def test_lock(self):
        """ Check double-lock raises exception after 60s (in 0.1s) """
        with partition.MtabLock():
            # speedup the process a bit
            (flexmock(time).should_receive("time").and_return(1)
             .and_return(2).and_return(62))
            self.assertRaises(partition.PartitionError,
                              partition.MtabLock().__enter__)
            flexmock_teardown()


if __name__ == '__main__':
    unittest.main()
