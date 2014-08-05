#!/usr/bin/env python

import os
import unittest
import tempfile
import common
from staging import utils_cgroup
from autotest.client.shared import error

# Mount file content, Controllers and mount points from RHEL-6
mount_1 = """rootfs / rootfs rw 0 0
proc /proc proc rw,relatime 0 0
sysfs /sys sysfs rw,seclabel,relatime 0 0
devtmpfs /dev devtmpfs rw,seclabel,relatime,size=3955196k,nr_inodes=988799,mode=755 0 0
devpts /dev/pts devpts rw,seclabel,relatime,gid=5,mode=620,ptmxmode=000 0 0
tmpfs /dev/shm tmpfs rw,seclabel,relatime 0 0
/dev/sda1 / ext4 rw,seclabel,relatime,barrier=1,data=ordered 0 0
none /selinux selinuxfs rw,relatime 0 0
devtmpfs /dev devtmpfs rw,seclabel,relatime,size=3955196k,nr_inodes=988799,mode=755 0 0
/proc/bus/usb /proc/bus/usb usbfs rw,relatime 0 0
/dev/sda3 /data ext4 rw,seclabel,relatime,barrier=1,data=ordered 0 0
none /proc/sys/fs/binfmt_misc binfmt_misc rw,relatime 0 0
sunrpc /var/lib/nfs/rpc_pipefs rpc_pipefs rw,relatime 0 0
nfsd /proc/fs/nfsd nfsd rw,relatime 0 0
cgroup /cgroup/cpuset cgroup rw,relatime,cpuset 0 0
cgroup /cgroup/cpu cgroup rw,relatime,cpu 0 0
cgroup /cgroup/cpuacct cgroup rw,relatime,cpuacct 0 0
cgroup /cgroup/memory cgroup rw,relatime,memory 0 0
cgroup /cgroup/devices cgroup rw,relatime,devices 0 0
cgroup /cgroup/freezer cgroup rw,relatime,freezer 0 0
cgroup /cgroup/net_cls cgroup rw,relatime,net_cls 0 0
cgroup /cgroup/blkio cgroup rw,relatime,blkio 0 0
"""
controllers_1 = [
    "cpuset",
    "cpu",
    "cpuacct",
    "memory",
    "devices",
    "freezer",
    "net_cls",
    "blkio",
]
mount_points_1 = [
    "/cgroup/cpuset",
    "/cgroup/cpu",
    "/cgroup/cpuacct",
    "/cgroup/memory",
    "/cgroup/devices",
    "/cgroup/freezer",
    "/cgroup/net_cls",
    "/cgroup/blkio",
]

# Mount file content, Controllers and mount points from RHEL-7
mount_2 = """rootfs / rootfs rw 0 0
proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0
sysfs /sys sysfs rw,seclabel,nosuid,nodev,noexec,relatime 0 0
devtmpfs /dev devtmpfs rw,seclabel,nosuid,size=3886908k,nr_inodes=971727,mode=755 0 0
securityfs /sys/kernel/security securityfs rw,nosuid,nodev,noexec,relatime 0 0
selinuxfs /sys/fs/selinux selinuxfs rw,relatime 0 0
tmpfs /dev/shm tmpfs rw,seclabel,nosuid,nodev 0 0
devpts /dev/pts devpts rw,seclabel,nosuid,noexec,relatime,gid=5,mode=620,ptmxmode=000 0 0
tmpfs /run tmpfs rw,seclabel,nosuid,nodev,mode=755 0 0
tmpfs /sys/fs/cgroup tmpfs rw,seclabel,nosuid,nodev,noexec,mode=755 0 0
cgroup /sys/fs/cgroup/systemd cgroup rw,nosuid,nodev,noexec,relatime,xattr,release_agent=/usr/lib/systemd/systemd-cgroups-agent,name=systemd 0 0
pstore /sys/fs/pstore pstore rw,nosuid,nodev,noexec,relatime 0 0
cgroup /sys/fs/cgroup/cpuset cgroup rw,nosuid,nodev,noexec,relatime,cpuset 0 0
cgroup /sys/fs/cgroup/cpu,cpuacct cgroup rw,nosuid,nodev,noexec,relatime,cpuacct,cpu 0 0
cgroup /sys/fs/cgroup/memory cgroup rw,nosuid,nodev,noexec,relatime,memory 0 0
cgroup /sys/fs/cgroup/devices cgroup rw,nosuid,nodev,noexec,relatime,devices 0 0
cgroup /sys/fs/cgroup/freezer cgroup rw,nosuid,nodev,noexec,relatime,freezer 0 0
cgroup /sys/fs/cgroup/net_cls cgroup rw,nosuid,nodev,noexec,relatime,net_cls 0 0
cgroup /sys/fs/cgroup/blkio cgroup rw,nosuid,nodev,noexec,relatime,blkio 0 0
cgroup /sys/fs/cgroup/perf_event cgroup rw,nosuid,nodev,noexec,relatime,perf_event 0 0
cgroup /sys/fs/cgroup/hugetlb cgroup rw,nosuid,nodev,noexec,relatime,hugetlb 0 0
/dev/mapper/rhel-root / xfs rw,seclabel,relatime,attr2,inode64,noquota 0 0
systemd-1 /proc/sys/fs/binfmt_misc autofs rw,relatime,fd=35,pgrp=1,timeout=300,minproto=5,maxproto=5,direct 0 0
debugfs /sys/kernel/debug debugfs rw,relatime 0 0
mqueue /dev/mqueue mqueue rw,seclabel,relatime 0 0
hugetlbfs /dev/hugepages hugetlbfs rw,seclabel,relatime 0 0
configfs /sys/kernel/config configfs rw,relatime 0 0
sunrpc /var/lib/nfs/rpc_pipefs rpc_pipefs rw,relatime 0 0
sunrpc /proc/fs/nfsd nfsd rw,relatime 0 0
/dev/sda1 /boot xfs rw,seclabel,relatime,attr2,inode64,noquota 0 0
/dev/mapper/rhel-home /home xfs rw,seclabel,relatime,attr2,inode64,noquota 0 0
binfmt_misc /proc/sys/fs/binfmt_misc binfmt_misc rw,relatime 0 0
"""
controllers_2 = [
    "systemd",
    "cpuset",
    "cpu",
    "cpuacct",
    "memory",
    "devices",
    "freezer",
    "net_cls",
    "blkio",
    "perf_event",
    "hugetlb",
]
mount_points_2 = [
    "/sys/fs/cgroup/systemd",
    "/sys/fs/cgroup/cpuset",
    "/sys/fs/cgroup/cpu,cpuacct",
    "/sys/fs/cgroup/cpu,cpuacct",
    "/sys/fs/cgroup/memory",
    "/sys/fs/cgroup/devices",
    "/sys/fs/cgroup/freezer",
    "/sys/fs/cgroup/net_cls",
    "/sys/fs/cgroup/blkio",
    "/sys/fs/cgroup/perf_event",
    "/sys/fs/cgroup/hugetlb",
]

mount_cases = [
    {"mount_txt": mount_1,
     "controllers": controllers_1,
     "mount_points": mount_points_1,
     },
    {"mount_txt": mount_2,
     "controllers": controllers_2,
     "mount_points": mount_points_2,
     },
]


class CgroupTest(unittest.TestCase):

    def test_get_cgroup_mountpoint(self):
        for case in mount_cases:
            # Let's work around the fact that NamedTemporaryFile
            # on py 2.4 doesn't have the delete param
            mount_file = tempfile.NamedTemporaryFile()
            mount_file_path = mount_file.name
            mount_file.close()

            # Now let's do our own management of the file
            mount_file = open(mount_file_path, 'w')
            mount_file.write(case["mount_txt"])
            mount_file.close()

            try:
                for idx, controller in enumerate(case["controllers"]):
                    res = utils_cgroup.get_cgroup_mountpoint(
                        controller, mount_file_path)
                    self.assertEqual(case["mount_points"][idx], res)
                self.assertRaises(
                    error.TestError,
                    utils_cgroup.get_cgroup_mountpoint,
                    "non_exit_ctlr",
                    mount_file_path)
            finally:
                os.remove(mount_file_path)

if __name__ == '__main__':
    unittest.main()
