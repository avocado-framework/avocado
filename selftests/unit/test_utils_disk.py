import unittest.mock

from avocado.utils import disk, process

LSBLK_OUTPUT = b'''
{
   "blockdevices": [
      {"name": "/dev/vda", "maj:min": "252:0", "rm": "0", "size": "6G", "ro": "0", "type": "disk", "mountpoint": null,
         "children": [
            {"name": "/dev/vda1", "maj:min": "252:1", "rm": "0", "size": "1M", "ro": "0", "type": "part", "mountpoint": null},
            {"name": "/dev/vda2", "maj:min": "252:2", "rm": "0", "size": "1G", "ro": "0", "type": "part", "mountpoint": "/boot"},
            {"name": "/dev/vda3", "maj:min": "252:3", "rm": "0", "size": "615M", "ro": "0", "type": "part", "mountpoint": "[SWAP]"},
            {"name": "/dev/vda4", "maj:min": "252:4", "rm": "0", "size": "4.4G", "ro": "0", "type": "part", "mountpoint": "/"}
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

    def test_empty(self):
        mock_result = process.CmdResult(
            command='lsblk --json --paths --inverse',
            stdout=b'{"blockdevices": []}')
        with unittest.mock.patch('avocado.utils.disk.process.run',
                                 return_value=mock_result):
            self.assertEqual(disk.get_disks(), [])

    def test_disks(self):
        mock_result = process.CmdResult(
            command='lsblk --json --paths --inverse',
            stdout=LSBLK_OUTPUT)
        with unittest.mock.patch('avocado.utils.disk.process.run',
                                 return_value=mock_result):
            self.assertEqual(disk.get_disks(), ['/dev/vda'])

    def test_get_filesystems(self):
        expected_fs = ['dax', 'bpf', 'pipefs', 'hugetlbfs', 'devpts', 'ext3']
        open_mocked = unittest.mock.mock_open(read_data=PROC_FILESYSTEMS)
        with unittest.mock.patch('builtins.open', open_mocked):
            self.assertEqual(sorted(expected_fs),
                             sorted(disk.get_available_filesystems()))

    def test_get_filesystem_type_default_root(self):
        open_mocked = unittest.mock.mock_open(read_data=PROC_MOUNTS)
        with unittest.mock.patch('builtins.open', open_mocked):
            self.assertEqual('ext4', disk.get_filesystem_type())

    def test_get_filesystem_type(self):
        open_mocked = unittest.mock.mock_open(read_data=PROC_MOUNTS)
        with unittest.mock.patch('builtins.open', open_mocked):
            self.assertEqual('ext2', disk.get_filesystem_type(mount_point='/home'))


if __name__ == '__main__':
    unittest.main()
