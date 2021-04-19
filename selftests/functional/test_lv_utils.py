"""
avocado.utils.lv_utils selftests
:author: Lukas Doktor <ldoktor@redhat.com>
:copyright: 2016 Red Hat, Inc
"""

import glob
import os
import sys
import time
import unittest

from avocado.utils import linux_modules, lv_utils, process
from selftests.utils import TestCaseTmpDir


class LVUtilsTest(TestCaseTmpDir):

    """
    Check the LVM related utilities
    """

    @unittest.skipIf(sys.platform.startswith('darwin'),
                     'macOS does not support LVM')
    @unittest.skipIf(process.system("which vgs", ignore_status=True),
                     "LVM utils not installed (command vgs is missing)")
    @unittest.skipIf(not process.can_sudo(), "This test requires root or "
                     "passwordless sudo configured.")
    def setUp(self):
        super(LVUtilsTest, self).setUp()
        self.vgs = []

    def tearDown(self):
        self.tmpdir.cleanup()
        for vg_name in self.vgs:
            lv_utils.vg_remove(vg_name)

    @unittest.skipIf(sys.platform.startswith('darwin'),
                     'macOS does not support LVM')
    @unittest.skipIf(process.system("vgs --all | grep -q avocado_testing_vg_"
                                    "e5kj3erv11a; [ $? -ne 0 ]", sudo=True,
                                    shell=True, ignore_status=True),
                     "Unittest volume group already exists.")
    def test_basic_workflow(self):
        """
        Check the basic workflow works using ramdisk
        """
        ramdisk_filename = vg_ramdisk_dir = loop_device = None
        vg_name = "avocado_testing_vg_e5kj3erv11a"
        lv_name = "avocado_testing_lv_lk0ff33al5h"
        ramdisk_basedir = os.path.join(self.tmpdir.name, "foo", "bar")
        mount_loc = os.path.join(self.tmpdir.name, "lv_mount_location")
        os.mkdir(mount_loc)
        try:
            # Create ramdisk vg
            self.assertFalse(os.path.exists(ramdisk_basedir))
            self.assertFalse(lv_utils.vg_check(vg_name))
            spec = lv_utils.vg_ramdisk(False, vg_name, 10, ramdisk_basedir,
                                       "sparse_file")
            ramdisk_filename, vg_ramdisk_dir, vg_name, loop_device = spec
            # Check it was created properly
            self.assertTrue(ramdisk_filename)
            self.assertTrue(vg_ramdisk_dir)
            self.assertTrue(vg_name)
            self.assertTrue(loop_device)
            self.assertTrue(os.path.exists(ramdisk_basedir))
            self.assertTrue(glob.glob(os.path.join(ramdisk_basedir, "*")))
            self.assertTrue(lv_utils.vg_check(vg_name))
            vgs = lv_utils.vg_list()
            self.assertIn(vg_name, vgs)
            # Can't create existing vg
            self.assertRaises(lv_utils.LVException, lv_utils.vg_create,
                              vg_name, loop_device)
            # Create and check LV
            lv_utils.lv_create(vg_name, lv_name, 1)
            lv_utils.lv_check(vg_name, lv_name)
            self.assertIn(vg_name, process.run("lvs --all",
                                               sudo=True).stdout_text)
            self.assertIn(lv_name, lv_utils.lv_list())
            lv_utils.lv_mount(vg_name, lv_name, mount_loc, "ext2")
            lv_utils.lv_umount(vg_name, lv_name)
            lv_utils.lv_remove(vg_name, lv_name)
            self.assertNotIn(lv_name, lv_utils.lv_list())
            # Cleanup ramdisk vgs
            lv_utils.vg_ramdisk_cleanup(ramdisk_filename, vg_ramdisk_dir,
                                        vg_name, loop_device)
            self.assertTrue(os.path.exists(ramdisk_basedir))
            self.assertFalse(glob.glob(os.path.join(ramdisk_basedir, "*")))
        except BaseException as details:
            try:
                process.run("mountpoint %s && umount %s"
                            % (mount_loc, mount_loc), shell=True, sudo=True)
            except BaseException as details:
                print("Fail to unmount LV: %s" % details)
            try:
                lv_utils.lv_remove(vg_name, lv_name)
            except BaseException as details:
                print("Fail to cleanup LV: %s" % details)
            try:
                lv_utils.vg_ramdisk_cleanup(ramdisk_filename, vg_ramdisk_dir,
                                            vg_name, loop_device)
            except BaseException as details:
                print("Fail to cleanup vg_ramdisk: %s" % details)


class DiskSpace(unittest.TestCase):

    @unittest.skipIf(process.system("modinfo scsi_debug", shell=True,
                                    ignore_status=True),
                     "Kernel mod 'scsi_debug' not available.")
    @unittest.skipIf(linux_modules.module_is_loaded("scsi_debug"),
                     "Kernel mod 'scsi_debug' is already loaded.")
    @unittest.skipIf(sys.platform.startswith('darwin'),
                     'macOS does not support scsi_debug module')
    @unittest.skipIf(not process.can_sudo(), "This test requires root or "
                     "passwordless sudo configured.")
    def test_get_diskspace(self):
        """
        Use scsi_debug device to check disk size
        """
        pre = glob.glob("/dev/sd*")
        process.system("modprobe scsi_debug", sudo=True)
        disks = set(glob.glob("/dev/sd*")).difference(pre)
        self.assertEqual(len(disks), 1, "pre: %s\npost: %s"
                         % (disks, glob.glob("/dev/sd*")))
        disk = disks.pop()
        self.assertEqual(lv_utils.get_diskspace(disk), "8388608")

    def tearDown(self):
        for _ in range(10):
            if process.run("modprobe -r scsi_debug",
                           ignore_status=True,
                           sudo=True).exit_status == 0:
                return
            time.sleep(0.05)
        raise RuntimeError("Failed to remove scsi_debug after testing")


if __name__ == '__main__':
    unittest.main()
