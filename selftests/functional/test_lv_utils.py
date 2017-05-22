"""
avocado.utils.lv_utils selftests
:author: Lukas Doktor <ldoktor@redhat.com>
:copyright: 2016 Red Hat, Inc
"""
from __future__ import print_function
from avocado.utils import process, lv_utils
import glob
import os
import sys
import shutil
import tempfile
import unittest


class LVUtilsTest(unittest.TestCase):

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
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.vgs = []

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        for vg_name in self.vgs:
            lv_utils.vg_remove(vg_name)

    @unittest.skipIf(sys.platform.startswith('darwin'),
                     'macOS does not support LVM')
    @unittest.skipIf(process.system("modinfo scsi_debug", shell=True,
                                    ignore_status=True),
                     "Kernel mod 'scsi_debug' not available.")
    @unittest.skipIf(process.system("lsmod | grep -q scsi_debug; [ $? -ne 0 ]",
                                    shell=True, ignore_status=True),
                     "Kernel mod 'scsi_debug' is already loaded.")
    def test_get_diskspace(self):
        """
        Use scsi_debug device to check disk size
        """
        pre = glob.glob("/dev/sd*")
        try:
            process.system("modprobe scsi_debug", sudo=True)
            disks = set(glob.glob("/dev/sd*")).difference(pre)
            self.assertEqual(len(disks), 1, "pre: %s\npost: %s"
                             % (disks, glob.glob("/dev/sd*")))
            disk = disks.pop()
            self.assertEqual(lv_utils.get_diskspace(disk), "8388608")
        except BaseException:
            for _ in xrange(10):
                res = process.run("rmmod scsi_debug", ignore_status=True,
                                  sudo=True)
                if not res.exit_status:
                    print("scsi_debug removed")
                    break
            else:
                print("Fail to remove scsi_debug: %s" % res)
        for _ in xrange(10):
            res = process.run("rmmod scsi_debug", ignore_status=True,
                              sudo=True)
            if not res.exit_status:
                break
        else:
            self.fail("Fail to remove scsi_debug after testing: %s" % res)

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
        ramdisk_basedir = os.path.join(self.tmpdir, "foo", "bar")
        mount_loc = os.path.join(self.tmpdir, "lv_mount_location")
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
            self.assertIn(vg_name, process.system_output("lvs --all",
                                                         sudo=True))
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
            raise


if __name__ == '__main__':
    unittest.main()
