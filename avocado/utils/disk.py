# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# This code was inspired in the autotest project,
#
# client/base_utils.py
#
# Copyright: 2018 IBM
# Authors : Praveen K Pandey <praveen@linux.vnet.ibm.com>
#           Narasimhan V <sim@linux.vnet.ibm.com>


"""
Disk utilities
"""


import json
import os
import re

from avocado.utils import process


class DiskError(Exception):
    """
    Generic DiskError
    """


def freespace(path):
    fs_stats = os.statvfs(path)
    return fs_stats.f_bsize * fs_stats.f_bavail


def get_disk_blocksize(path):
    """Return the disk block size, in bytes"""
    fs_stats = os.statvfs(path)
    return fs_stats.f_bsize


def create_loop_device(size, blocksize=4096, directory='./'):
    """
    Creates a loop device of size and blocksize specified.

    :param size: Size of loop device, in bytes
    :type size: int
    :param blocksize: block size of loop device, in bytes. Defaults to 4096
    :type blocksize: int
    :param directory: Directory where the backing file will be created.
                      Defaults to current directory.
    :type directory: str

    :return: loop device name
    :rtype: str
    """
    cmd = "losetup --find"
    loop = process.run(cmd, ignore_status=True,
                       sudo=True).stdout_text.strip('\n')

    loop_file = os.path.join(directory,
                             "tmp_%s.img" % loop.split('/')[-1])
    cmd = "dd if=/dev/zero of={} bs={} count={}".format(loop_file,
                                                        blocksize,
                                                        int(size / blocksize))
    if process.system(cmd, ignore_status=True, sudo=True) != 0:
        raise DiskError("Unable to create backing file for loop device")

    cmd = "losetup %s %s -P" % (loop, loop_file)
    if process.system(cmd, ignore_status=True, sudo=True) != 0:
        raise DiskError("Unable to create the loop device")
    return loop


def delete_loop_device(device):
    """
    Deletes the specified loop device.

    :param device: device to be deleted
    :type device: str

    :return: True if deleted.
    :rtype: bool
    """
    cmd = "losetup -aJl"
    loop_dic = json.loads(process.run(cmd, ignore_status=True,
                                      sudo=True).stdout_text)
    loop_file = ''
    for loop_dev in loop_dic['loopdevices']:
        if device == loop_dev['name']:
            loop_file = loop_dev['back-file']
    if not loop_file:
        raise DiskError("Unable to find backing file for loop device")
    cmd = "losetup -d %s" % device
    if process.system(cmd, ignore_status=True, sudo=True) != 0:
        raise DiskError("Unable to delete the loop device")
    os.remove(loop_file)
    return True


def get_disks():
    """
    Returns the physical "hard drives" available on this system

    This is a simple wrapper around `lsblk` and will return all the
    top level physical (non-virtual) devices return by it.

    TODO: this is currently Linux specific.  Support for other
    platforms is desirable and may be implemented in the future.

    :returns: a list of paths to the physical disks on the system
    :rtype: list of str
    """
    json_result = process.run('lsblk --json --paths --inverse')
    json_data = json.loads(json_result.stdout_text)
    return [str(disk['name']) for disk in json_data['blockdevices']]


def get_available_filesystems():
    """
    Return a list of all available filesystem types

    :returns: a list of filesystem types
    :rtype: list of str
    """
    filesystems = set()
    with open('/proc/filesystems') as proc_fs:
        for proc_fs_line in proc_fs.readlines():
            filesystems.add(re.sub(r'(nodev)?\s*', '', proc_fs_line))
    return list(filesystems)


def get_filesystem_type(mount_point='/'):
    """
    Returns the type of the filesystem of mount point informed.
    The default mount point considered when none is informed
    is the root "/" mount point.

    :param str mount_point: mount point to asses the filesystem type.
                            Default "/"
    :returns: filesystem type
    :rtype: str
    """
    with open('/proc/mounts') as mounts:
        for mount_line in mounts.readlines():
            _, fs_file, fs_vfstype, _, _, _ = mount_line.split()
            if fs_file == mount_point:
                return fs_vfstype


def is_root_device(device):
    """
    check for root disk

    :param device: device to check
    :returns: True or False, True if given device is root disk
              otherwise will return False.
    """
    cmd = "lsblk --j -o MOUNTPOINT,PKNAME"
    output = process.run(cmd)
    result = json.loads(output.stdout_text)
    for item in result['blockdevices']:
        if item['mountpoint'] == "/" and device == str(item['pkname']):
            return True
    return False
