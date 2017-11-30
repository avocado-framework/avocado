"""
avocado.utils.partition unittests
:author: Lukas Doktor <ldoktor@redhat.com>
:copyright: 2016 Red Hat, Inc
"""

import os
import shutil
import tempfile
import unittest     # pylint: disable=C0411
try:
    from unittest import mock
except ImportError:
    import mock

from avocado.utils import partition, process
from avocado.utils import path as utils_path


def missing_binary(binary):
    try:
        utils_path.find_command(binary)
        return False
    except utils_path.CmdNotFoundError:
        return True


class TestPartition(unittest.TestCase):

    """
    Unit tests for avocado.utils.partition
    """

    @unittest.skipIf(not os.path.isdir('/proc/mounts'),
                     'system does not have /proc/mounts')
    @unittest.skipIf(not process.can_sudo('mount'),
                     'current user must be allowed to run "mount" under sudo')
    @unittest.skipIf(not process.can_sudo('mkfs.ext2 -V'),
                     'current user must be allowed to run "mkfs.ext2" under '
                     'sudo')
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
        with open("/proc/mounts") as proc_mounts_file:
            proc_mounts = proc_mounts_file.read()
            self.assertIn(self.mountpoint, proc_mounts)
            self.assertEqual(self.mountpoint, self.disk.get_mountpoint())
            self.disk.unmount()
        with open("/proc/mounts") as proc_mounts_file:
            proc_mounts = proc_mounts_file.read()
            self.assertNotIn(self.mountpoint, proc_mounts)

    @unittest.skipIf(not process.can_sudo('kill -l'),
                     "requires running kill as a privileged user")
    def test_force_unmount(self):
        """ Test force-unmount feature """
        self.disk.mkfs()
        self.disk.mount()
        with open("/proc/mounts") as proc_mounts_file:
            proc_mounts = proc_mounts_file.read()
            self.assertIn(self.mountpoint, proc_mounts)
            proc = process.SubProcess("cd %s; while :; do echo a > a; rm a; done"
                                      % self.mountpoint, shell=True)
            proc.start()
            self.assertTrue(self.disk.unmount())
            self.assertEqual(proc.poll(), -9)   # Process should be killed -9
        with open("/proc/mounts") as proc_mounts_file:
            proc_mounts = proc_mounts_file.read()
            self.assertNotIn(self.mountpoint, proc_mounts)

    def test_double_mount(self):
        """ Check the attempt for second mount fails """
        self.disk.mkfs()
        self.disk.mount()
        with open("/proc/mounts") as proc_mounts_file:
            proc_mounts = proc_mounts_file.read()
            self.assertIn(self.mountpoint, proc_mounts)
            self.assertRaises(partition.PartitionError, self.disk.mount)
            self.assertIn(self.mountpoint, proc_mounts)

    def test_double_umount(self):
        """ Check double unmount works well """
        self.disk.mkfs()
        self.disk.mount()
        with open("/proc/mounts") as proc_mounts_file:
            proc_mounts = proc_mounts_file.read()
            self.assertIn(self.mountpoint, proc_mounts)
        self.disk.unmount()
        with open("/proc/mounts") as proc_mounts_file:
            proc_mounts = proc_mounts_file.read()
            self.assertNotIn(self.mountpoint, proc_mounts)
        self.disk.unmount()
        with open("/proc/mounts") as proc_mounts_file:
            proc_mounts = proc_mounts_file.read()
            self.assertNotIn(self.mountpoint, proc_mounts)

    def test_format_mounted(self):
        """ Check format on mounted device fails """
        self.disk.mkfs()
        self.disk.mount()
        with open("/proc/mounts") as proc_mounts_file:
            proc_mounts = proc_mounts_file.read()
            self.assertIn(self.mountpoint, proc_mounts)
        self.assertRaises(partition.PartitionError, self.disk.mkfs)

    def tearDown(self):
        self.disk.unmount()
        shutil.rmtree(self.tmpdir)


@unittest.skipIf(not os.path.isfile('/etc/mtab'),
                 'macOS does not have /etc/mtab')
class TestMtabLock(unittest.TestCase):

    """
    Unit tests for avocado.utils.partition
    """

    def test_lock(self):
        """ Check double-lock raises exception after 60s (in 0.1s) """
        with partition.MtabLock():
            with mock.patch('avocado.utils.partition.time.time',
                            mock.MagicMock(side_effect=[1, 2, 62])):
                self.assertRaises(partition.PartitionError,
                                  partition.MtabLock().__enter__)


if __name__ == '__main__':
    unittest.main()
