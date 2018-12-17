import sys
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from .. import recent_mock
from avocado.utils import disk
from avocado.utils import process


LSBLK_OUTPUT = b'''
{
   "blockdevices": [
      {"name": "vda", "maj:min": "252:0", "rm": "0", "size": "6G", "ro": "0", "type": "disk", "mountpoint": null,
         "children": [
            {"name": "vda1", "maj:min": "252:1", "rm": "0", "size": "1M", "ro": "0", "type": "part", "mountpoint": null},
            {"name": "vda2", "maj:min": "252:2", "rm": "0", "size": "1G", "ro": "0", "type": "part", "mountpoint": "/boot"},
            {"name": "vda3", "maj:min": "252:3", "rm": "0", "size": "615M", "ro": "0", "type": "part", "mountpoint": "[SWAP]"},
            {"name": "vda4", "maj:min": "252:4", "rm": "0", "size": "4.4G", "ro": "0", "type": "part", "mountpoint": "/"}
         ]
      }
   ]
}'''


PROC_FILESYSTEMS = (
    'nodev   dax\n' +
    'nodev   bpf\n' +
    'nodev   pipefs\n' +
    'nodev   hugetlbfs\n' +
    'nodev   devpts\n' +
    '        ext3'
)

PROC_MOUNTS = (
    "/dev/mapper/fedora-root / ext4 rw,seclabel,relatime 0 0\n" +
    "/dev/mapper/fedora-home /home ext2 rw,seclabel,relatime 0 0\n" +
    "sysfs /sys sysfs rw,seclabel,nosuid,nodev,noexec,relatime 0 0\n" +
    "proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0"
)


class Disk(unittest.TestCase):

    @property
    def builtin_open(self):
        py_version = sys.version_info[0]
        return 'builtins.open' if py_version == 3 else '__builtin__.open'

    def test_empty(self):
        mock_result = process.CmdResult(
            command='lsblk --json',
            stdout=b'{"blockdevices": []}')
        with mock.patch('avocado.utils.disk.process.run',
                        return_value=mock_result):
            self.assertEqual(disk.get_disks(), [])

    def test_disks(self):
        mock_result = process.CmdResult(
            command='lsblk --json',
            stdout=LSBLK_OUTPUT)
        with mock.patch('avocado.utils.disk.process.run',
                        return_value=mock_result):
            self.assertEqual(disk.get_disks(), ['/dev/vda'])

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_get_filesystems(self):
        expected_fs = ['dax', 'bpf', 'pipefs', 'hugetlbfs', 'devpts', 'ext3']
        open_mocked = mock.mock_open(read_data=PROC_FILESYSTEMS)
        with mock.patch(self.builtin_open, open_mocked):
            self.assertEqual(sorted(expected_fs),
                             sorted(disk.get_available_filesystems()))

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_get_filesystem_type_default_root(self):
        open_mocked = mock.mock_open(read_data=PROC_MOUNTS)
        with mock.patch(self.builtin_open, open_mocked):
            self.assertEqual('ext4', disk.get_filesystem_type())

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_get_filesystem_type(self):
        open_mocked = mock.mock_open(read_data=PROC_MOUNTS)
        with mock.patch(self.builtin_open, open_mocked):
            self.assertEqual('ext2', disk.get_filesystem_type(mount_point='/home'))


if __name__ == '__main__':
    unittest.main()
