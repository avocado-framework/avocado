import unittest

try:
    from unittest import mock
except ImportError:
    import mock


from avocado.utils import disk
from avocado.utils import process


class Disk(unittest.TestCase):

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
            stdout=self.LSBLK_OUTPUT)
        with mock.patch('avocado.utils.disk.process.run',
                        return_value=mock_result):
            self.assertEqual(disk.get_disks(), ['/dev/vda'])


if __name__ == '__main__':
    unittest.main()
