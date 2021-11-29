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
# Copyright: 2016 Red Hat, Inc.
# Author: Lukas Doktor <ldoktor@redhat.com>
#
# Based on code by: Martin Bligh (mbligh@google.com)
#     Copyright: Google 2006-2008
#     https://github.com/autotest/autotest/blob/master/client/partition.py

"""
Utility for handling partitions.
"""

import hashlib
import logging
import os
import tempfile

from avocado.utils import filelock, process

LOG = logging.getLogger(__name__)


class PartitionError(Exception):

    """
    Generic PartitionError
    """

    def __init__(self, partition, reason, details=None):
        msg = reason + ": " + str(details) if details else reason
        super(PartitionError, self).__init__(msg)
        self.partition = partition

    def __str__(self):
        return "Partition(%s): %s" % (self.partition.device,
                                      super(PartitionError, self).__str__())


class MtabLock:
    device = "/etc/mtab"

    def __init__(self, timeout=60):
        self.timeout = timeout
        self.mtab = None
        device_hash = hashlib.sha1(self.device.encode("utf-8")).hexdigest()
        lock_filename = os.path.join(tempfile.gettempdir(), device_hash)
        self.lock = filelock.FileLock(lock_filename, timeout=self.timeout)

    def __enter__(self):
        try:
            self.lock.__enter__()
        except (filelock.LockFailed, filelock.AlreadyLocked) as e:
            reason = "Unable to obtain '%s' lock in %ds" % (self.device,
                                                            self.timeout)
            raise PartitionError(self, reason, e)
        self.mtab = open(self.device)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.mtab:
            self.mtab.close()
        self.lock.__exit__(exc_type, exc_value, exc_traceback)


class Partition:

    """
    Class for handling partitions and filesystems
    """

    def __init__(self, device, loop_size=0, mountpoint=None, mkfs_flags='', mount_options=None):
        """
        :param device: The device in question (e.g."/dev/hda2"). If device is a
                file it will be mounted as loopback.
        :param loop_size: Size of loopback device (in MB). Defaults to 0.
        :param mountpoint: Where the partition to be mounted to.
        :param mkfs_flags: Optional flags for mkfs
        :param mount_options: Add mount options optionally
        """
        self.device = device
        self.loop = loop_size
        self.fstype = None
        self.mountpoint = mountpoint
        self.mkfs_flags = mkfs_flags
        self.mount_options = mount_options
        if self.loop:
            process.run('dd if=/dev/zero of=%s bs=1M count=%d'
                        % (device, self.loop))

    def __repr__(self):
        return '<Partition: %s>' % self.device

    @staticmethod
    def list_mount_devices():
        """
        Lists mounted file systems and swap on devices.
        """
        # list mounted file systems
        devices = [line.split()[0]
                   for line in process.getoutput('mount').splitlines()]
        # list mounted swap devices
        swaps = process.getoutput('swapon -s').splitlines()
        devices.extend([line.split()[0] for line in swaps
                        if line.startswith('/')])
        return devices

    @staticmethod
    def list_mount_points():
        """
        Lists the mount points.
        """
        return [line.split()[2]
                for line in process.getoutput('mount').splitlines()]

    def get_mountpoint(self, filename=None):
        """
        Find the mount point of this partition object.

        :param filename: where to look for the mounted partitions information
                (default None which means it will search /proc/mounts and/or
                /etc/mtab)

        :return: a string with the mount point of the partition or None if not
                mounted
        """
        # Try to match this device/mountpoint
        if filename:
            with open(filename) as open_file:
                for line in open_file:
                    parts = line.split()
                    if parts[0] == self.device and parts[1] == self.mountpoint:
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

    def mkfs(self, fstype=None, args=''):
        """
        Format a partition to filesystem type

        :param fstype: the filesystem type, such as "ext3", "ext2". Defaults
                       to previously set type or "ext2" if none has set.
        :param args: arguments to be passed to mkfs command.
        """

        if self.device in self.list_mount_devices():
            raise PartitionError(self, 'Unable to format mounted device')

        if not fstype:
            if self.fstype:
                fstype = self.fstype
            else:
                fstype = 'ext2'

        if self.mkfs_flags:
            args += ' ' + self.mkfs_flags
        if fstype in ['xfs', 'btrfs']:
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

        mkfs_cmd = "mkfs %s %s" % (args, self.device)

        try:
            process.system_output("yes | %s" % mkfs_cmd, shell=True)
        except process.CmdError as error:
            raise PartitionError(self, "Failed to mkfs", error)
        else:
            self.fstype = fstype

    def mount(self, mountpoint=None, fstype=None, args='', mnt_check=True):
        """
        Mount this partition to a mount point

        :param mountpoint: If you have not provided a mountpoint to partition
                object or want to use a different one, you may specify it here.
        :param fstype: Filesystem type. If not provided partition object value
                will be used.
        :param args: Arguments to be passed to "mount" command.
        :param mnt_check: Flag to check/avoid checking existing device/mountpoint
        """
        if not mountpoint:
            mountpoint = self.mountpoint
        if not mountpoint:
            raise PartitionError(self, "No mountpoint specified and no "
                                 "default provided to this partition object")
        if fstype is None:
            fstype = self.fstype
        else:
            self.fstype = fstype

        if self.mount_options:
            args += ' -o ' + self.mount_options
        if fstype:
            args += ' -t ' + fstype
        args = args.lstrip()

        with MtabLock():
            if mnt_check:
                if self.device in self.list_mount_devices():
                    raise PartitionError(self, "Attempted to mount mounted device")
                if mountpoint in self.list_mount_points():
                    raise PartitionError(self, "Attempted to mount busy directory")
            if not os.path.isdir(mountpoint):
                os.makedirs(mountpoint)
            try:
                if self.loop:
                    losetup_cmd = "losetup --find --show -f %s" % self.device
                    self.device = process.run(losetup_cmd,
                                              sudo=True).stdout_text.strip()
                process.system("mount %s %s %s"
                               % (args, self.device, mountpoint), sudo=True)
            except process.CmdError as details:
                raise PartitionError(self, "Mount failed", details)
        # Update the fstype as the mount command passed
        self.fstype = fstype

    def _get_pids_on_mountpoint(self, mnt):
        """
        Returns a list of processes using a given mountpoint
        """
        try:
            cmd = "lsof " + mnt
            out = process.system_output(cmd, sudo=True)
            return [int(line.split()[1]) for line in out.splitlines()[1:]]
        except OSError as details:
            msg = 'Could not run lsof to identify processes using "%s"' % mnt
            LOG.error(msg)
            raise PartitionError(self, msg, details)
        except process.CmdError as details:
            msg = 'Failure executing "%s"' % cmd
            LOG.error(msg)
            raise PartitionError(self, msg, details)

    def _unmount_force(self, mountpoint):
        """
        Kill all other jobs accessing this partition and force unmount it.

        :return: None
        :raise PartitionError: On critical failure
        """
        for pid in self._get_pids_on_mountpoint(mountpoint):
            try:
                process.system("kill -9 %d" % pid, ignore_status=True, sudo=True)
            except process.CmdError as details:
                raise PartitionError(self, "Failed to kill processes", details)
        # Unmount
        try:
            process.run("umount -f %s" % mountpoint, sudo=True)
        except process.CmdError as details:
            try:
                process.run("umount -l %s" % mountpoint, sudo=True)
            except process.CmdError as details:
                raise PartitionError(self, "Force unmount failed", details)

    def unmount(self, force=True):
        """
        Umount this partition.

        It's easier said than done to umount a partition.
        We need to lock the mtab file to make sure we don't have any
        locking problems if we are umounting in parallel.

        When the unmount fails and force==True we unmount the partition
        ungracefully.

        :return: 1 on success, 2 on force umount success
        :raise PartitionError: On failure
        """
        with MtabLock():
            mountpoint = self.get_mountpoint()
            result = 1
            if not mountpoint:
                LOG.debug('%s not mounted', self.device)
                return result
            try:
                process.run("umount " + mountpoint, sudo=True)
                result = 1
            except process.CmdError as details:
                if force:
                    LOG.debug("Standard umount failed on %s, forcing",
                              mountpoint)
                    self._unmount_force(mountpoint)
                    result = 2
                else:
                    raise PartitionError(self, "Unable to unmount gracefully",
                                         details)
        if self.loop:
            try:
                process.run("losetup -d %s" % self.device, sudo=True)
            except process.CmdError as details:
                raise PartitionError(self, "Unable to cleanup loop device",
                                     details)

        return result
