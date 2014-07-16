#!/usr/bin/python

import unittest

import common
import utils_params

BASE_DICT = {
    'image_boot': 'yes',
    'image_boot_stg': 'no',
    'image_chain': '',
    'image_clone_command': 'cp --reflink=auto %s %s',
    'image_format': 'qcow2',
    'image_format_stg': 'qcow2',
    'image_name': 'images/f18-64',
    'image_name_stg': 'enospc',
    'image_raw_device': 'no',
    'image_remove_command': 'rm -rf %s',
    'image_size': '10G',
    'image_snapshot_stg': 'no',
    'image_unbootable_pattern': 'Hard Disk.*not a bootable disk',
    'image_verify_bootable': 'yes',
    'images': 'image1 stg',
}

CORRECT_RESULT_MAPPING = {"image1": {'image_boot_stg': 'no',
                                     'image_snapshot_stg': 'no',
                                     'image_chain': '',
                                     'image_unbootable_pattern': 'Hard Disk.*not a bootable disk',
                                     'image_name': 'images/f18-64',
                                     'image_remove_command': 'rm -rf %s',
                                     'image_name_stg': 'enospc',
                                     'image_clone_command': 'cp --reflink=auto %s %s',
                                     'image_size': '10G', 'images': 'image1 stg',
                                     'image_raw_device': 'no',
                                     'image_format': 'qcow2',
                                     'image_boot': 'yes',
                                     'image_verify_bootable': 'yes',
                                     'image_format_stg': 'qcow2'},
                          "stg": {'image_snapshot': 'no',
                                  'image_boot_stg': 'no',
                                  'image_snapshot_stg': 'no',
                                  'image_chain': '',
                                  'image_unbootable_pattern': 'Hard Disk.*not a bootable disk',
                                  'image_name': 'enospc',
                                  'image_remove_command': 'rm -rf %s',
                                  'image_name_stg': 'enospc',
                                  'image_clone_command': 'cp --reflink=auto %s %s',
                                  'image_size': '10G',
                                  'images': 'image1 stg',
                                  'image_raw_device': 'no',
                                  'image_format': 'qcow2',
                                  'image_boot': 'no',
                                  'image_verify_bootable': 'yes',
                                  'image_format_stg': 'qcow2'}}


class TestParams(unittest.TestCase):

    def setUp(self):
        self.params = utils_params.Params(BASE_DICT)

    def testObjects(self):
        self.assertEquals(self.params.objects("images"), ['image1', 'stg'])

    def testObjectsParams(self):
        for key in CORRECT_RESULT_MAPPING.keys():
            self.assertEquals(self.params.object_params(key),
                              CORRECT_RESULT_MAPPING[key])

    def testGetItemMissing(self):
        try:
            self.params['bogus']
            raise ValueError("Did not get a ParamNotFound error when trying "
                             "to access a non-existing param")
        # pylint: disable=E0712
        except utils_params.ParamNotFound:
            pass

    def testGetItem(self):
        self.assertEqual(self.params['image_size'], "10G")


if __name__ == "__main__":
    unittest.main()
