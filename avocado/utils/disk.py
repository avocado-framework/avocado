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


"""
Disk utilities
"""


import os
import json
import re

from . import process


def freespace(path):
    fs_stats = os.statvfs(path)
    return fs_stats.f_bsize * fs_stats.f_bavail


def get_disk_blocksize(path):
    """Return the disk block size, in bytes"""
    fs_stats = os.statvfs(path)
    return fs_stats.f_bsize


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
    json_result = process.run('lsblk --json')
    json_data = json.loads(json_result.stdout_text)
    return ['/dev/%s' % str(disk['name']) for disk in json_data['blockdevices']]


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

    :param str mount_point: mount point to asses the filesystem type, default "/"
    :returns: filesystem type
    :rtype: str
    """
    with open('/proc/mounts') as mounts:
        for mount_line in mounts.readlines():
            _, fs_file, fs_vfstype, _, _, _ = mount_line.split()
            if fs_file == mount_point:
                return fs_vfstype
