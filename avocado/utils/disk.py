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
# Copyright: 2017 IBM
# Author: Narasimhan V sim@linux.vnet.ibm.com
#
# freespace() function was inspired in the autotest project,
# client/base_utils.py


"""
Disk utilities
"""

import logging
import os
from . import process


LOGGER = logging.getLogger('avocado.test')


class FSException(Exception):
    """
    Base Exception Class for all exceptions
    """
    pass


class DiskException(Exception):
    """
    Base Exception Class for all exceptions
    """


def freespace(path):
    """
    Gets freespace on the given path.
    """
    fs_stats = os.statvfs(path)
    return fs_stats.f_bsize * fs_stats.f_bavail


def zero_disk(disk_name):
    """
    Zero a disk.
    :param disk_name: Name of the disk
    """

    try:
        process.run("dd if=/dev/zero of=%s bs=4096 count=1" % disk_name)
    except process.CmdError, ex:
        raise DiskException("Fail to zero disk: %s" % ex)


def disk_mount(disk_name, mount_loc, create_filesystem="", args=""):
    """
    Mount a filesystem to a mount location.
    :param disk_name: Name of the disk
    :mount_loc: Location to mount the logical volume
    :param create_filesystem: Can be one of ext2, ext3, ext4, vfat or empty
    """

    try:
        if create_filesystem:
            process.run("mkfs.%s %s %s" %
                        (create_filesystem, args, disk_name),
                        sudo=True)
        process.run("mount %s %s" %
                    (disk_name, mount_loc), sudo=True)
    except process.CmdError, ex:
        raise FSException("Fail to mount fs: %s" % ex)


def disk_umount(disk_name):
    """
    Unmount a filesystem from a mount location.
    :param disk_name: Name of disk
    """

    try:
        process.run("umount %s" % disk_name, sudo=True)
    except process.CmdError, ex:
        raise FSException("Fail to unmount fs: %s" % ex)
