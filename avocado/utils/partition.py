#!/usr/bin/env python

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
# Copyright: 2016 IBM.
# Author: Rajashree Rajendran<rajashr7@linux.vnet.ibm.com>
#
# Based on the code by
# Author: Martin Bligh (mbligh@google.com)
# Copyright: Google 2006-2008

"""
Utility for handling creation, formatting of partitions.
"""

import fcntl
import logging
import os
import re
import sys

from . import process


class Partition(object):

    """
    Class for handling partitions and filesystems
    """

    def __init__(self, device, loop_size=0, mountpoint=None):
        """
        :param device: The device in question (e.g."/dev/hda2"). If device is a
                file it will be mounted as loopback.
        :param loop_size: Size of loopback device (in MB). Defaults to 0.
        :param mountpoint: The partition to be mounted.
        """
        self.device = device
        self.loop = loop_size
        self.fstype = None
        self.mountpoint = mountpoint
        self.mkfs_flags = None
        self.mount_options = None
        if self.loop:
            cmd = 'dd if=/dev/zero of=%s bs=1M count=%d' % (device, self.loop)
            process.run(cmd)

    def __repr__(self):
        return '<Partition: %s>' % self.device

    @staticmethod
    def list_mount_devices():
        """
        Lists mounted filesystems and swap on devices.
        """
        devices = []
        # list mounted filesystems
        for line in process.system_output('mount').splitlines():
            devices.append(line.split()[0])
        # list mounted swap devices
        for line in process.system_output('swapon -s').splitlines():
            if line.startswith('/'):    # skip header line
                devices.append(line.split()[0])
        return devices

    @staticmethod
    def list_mount_points():
        """
        Lists the mount points.
        """
        mountpoints = []
        for line in process.system_output('mount').splitlines():
            mountpoints.append(line.split()[2])
        return mountpoints

    def get_mountpoint(self, filename=None):
        """
        Find the mount point of this partition object.

        :param filename: where to look for the mounted partitions information
                (default None which means it will search /proc/mounts and/or
                /etc/mtab)

        :return: a string with the mount point of the partition or None if not
                mounted
        """

        if filename:
            for line in open(filename).readlines():
                parts = line.split()
                if parts[0] == self.device or parts[1] == self.mountpoint:
                    return parts[1]    # The mountpoint where it's mounted
            return None

        # no specific file given, look in /proc/mounts
        res = self.get_mountpoint(filename='/proc/mounts')
        if not res:
            # sometimes the root partition is reported as /dev/root in
            # /proc/mounts in this case, try /etc/mtab
            res = self.get_mountpoint(filename='/etc/mtab')

            if res != '/':
                res = None
        return res

    @staticmethod
    def mkfs_exec(fstype):
        """
        Return the proper mkfs executable based on fs
        """

        if fstype == 'ext4':
            if os.path.exists('/sbin/mkfs.ext4'):
                return 'mkfs'
        else:
            return 'mkfs'

        raise NameError('Error creating partition for filesystem type %s' %
                        fstype)

    def mkfs(self, fstype=None, args=''):
        """
        Format a partition to filesystem type

        :param fstype: the filesystem type, e.g.. "ext3", "ext2"
        :param args: arguments to be passed to mkfs command.
        """

        if self.list_mount_devices().count(self.device):
            raise NameError('Attempted to format mounted device %s' %
                            self.device)

        if not fstype:
            if self.fstype:
                fstype = self.fstype
            else:
                fstype = 'ext2'

        if self.mkfs_flags:
            args += ' ' + self.mkfs_flags
        if fstype == 'xfs':
            args += ' -f'

        if self.loop:
            if fstype.startswith('ext'):
                args += ' -F'
            elif fstype == 'reiserfs':
                args += ' -f'

        # If there isn't already a '-t <type>' argument, add one.
        if "-t" not in args:
            args = "-t %s %s" % (fstype, args)

        args = args.strip()

        mkfs_cmd = "%s %s %s" % (self.mkfs_exec(fstype), args, self.device)

        sys.stdout.flush()
        try:
            process.system_output("yes | %s" % mkfs_cmd, shell=True)
        except process.CmdError, error:
            logging.error(error)
        else:
            self.fstype = fstype

    def mount(self, mountpoint=None, fstype=None, args=''):
        """
        Mount this partition to a mount point

        :param mountpoint: If you have not provided a mountpoint to partition
                object or want to use a different one, you may specify it here.
        :param fstype: Filesystem type. If not provided partition object value
                will be used.
        :param args: Arguments to be passed to "mount" command.
        """

        if fstype is None:
            fstype = self.fstype
        else:
            self.fstype = fstype

        if self.mount_options:
            args += ' -o  ' + self.mount_options
        if fstype:
            args += ' -t ' + fstype
        if self.loop:
            args += ' -o loop'
        args = args.lstrip()

        if not mountpoint and not self.mountpoint:
            raise ValueError("No mountpoint specified and no default "
                             "provided to this partition object")
        if not mountpoint:
            mountpoint = self.mountpoint

        mount_cmd = "mount %s %s %s" % (args, self.device, mountpoint)

        if self.list_mount_devices().count(self.device):
            raise NameError('Attempted to mount mounted device')
        if self.list_mount_points().count(mountpoint):
            raise NameError('Attempted to mount busy mountpoint')

        mtab = open('/etc/mtab')
        fcntl.flock(mtab.fileno(), fcntl.LOCK_EX)
        sys.stdout.flush()
        if not os.path.isdir(mountpoint):
            os.makedirs(mountpoint)
        try:
            process.run(mount_cmd)
            mtab.close()
        except process.CmdError:
            mtab.close()
        else:
            self.fstype = fstype

    def unmount_force(self):
        """
        Kill all other jobs accessing this partition. Use fuser and ps to find
        all mounts on this mountpoint and unmount them.

        :return: true for success or false for any errors
        """

        logging.debug("Standard umount failed, will try forcing. Users:")
        try:
            cmd = 'fuser ' + self.get_mountpoint()
            logging.debug(cmd)
            fuser = process.system_output(cmd)
            logging.debug(fuser)
            users = re.sub('.*:', '', fuser).split()
            for user in users:
                match = re.match(r'(\d+)(.*)', user)
                (pid, usage) = (match.group(1), match.group(2))
                try:
                    proc_stat = process.system_output('ps -p %s | '
                                                      'sed 1d' % pid)
                    logging.debug(usage, pid, proc_stat)
                except process.CmdError:
                    pass
                process.run('ls -l ' + self.device)
                umount_cmd = "umount -f " + self.device
                process.run(umount_cmd)
                return True
        except process.CmdError:
            logging.debug('Umount_force failed for %s', self.device)
            return False

    def unmount(self):
        """
        Umount this partition.

        It's easier said than done to umount a partition.
        We need to lock the mtab file to make sure we don't have any
        locking problems if we are umounting in paralllel.

        If there turns out to be a problem with the simple umount we
        end up calling umount_force to get more  aggressive.
        """
        mountpoint = self.get_mountpoint()
        if not mountpoint:
            logging.error('umount for dev %s has no mountpoint', self.device)
            return

        umount_cmd = "umount " + mountpoint
        mtab = open('/etc/mtab')

        fcntl.flock(mtab.fileno(), fcntl.LOCK_EX)
        sys.stdout.flush()
        try:
            process.run(umount_cmd)
            mtab.close()
        except (process.CmdError, IOError):
            mtab.close()

            # Try the forceful umount
            if self.unmount_force():
                return
