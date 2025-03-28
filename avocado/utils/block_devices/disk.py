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
# Copyright: 2024 IBM
# Authors : Praveen K Pandey <praveen@linux.vnet.ibm.com>
#         : Narasimhan V <sim@linux.vnet.ibm.com>
#         : Naresh Bannoth <nbannoth@linux.vnet.ibm.com>


"""
Disk utilities
"""


import json
import logging
import os
import re

from avocado.utils import genio, multipath, process

LOGGER = logging.getLogger(__name__)


class DiskError(Exception):
    """
    Generic DiskError
    """


class DiskUtils:
    """
    Perform Disk related operations.
    """

    def __init__(self, disk, mount_point):
        """
        :param disk: Name of the disk, eg: /dev/nvme0n1, /dev/mapper/mpathX,
                     /dev/sdX etc..
        :type disk: str
        :param mount_point: It is the directory path, where the disk going
                            mounted or disk already mounted on this dir
                            eg: /mnt, /root/mnt etc..
        :type mount_point: str
        """
        self.disk = disk
        self.mount_point = mount_point

    def freespace(self):
        fs_stats = os.statvfs(self.disk)
        return fs_stats.f_bsize * fs_stats.f_bavail

    def get_disk_blocksize(self):
        """Return the disk block size, in bytes"""
        fs_stats = os.statvfs(self.disk)
        return fs_stats.f_bsize

    def create_loop_device(self, size, blocksize=4096, directory="./"):
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
        loop = process.run(cmd, ignore_status=True, sudo=True).stdout_text
        loop = loop.strip("\n")

        loop_file = os.path.join(directory, f"tmp_{loop.split('/')[-1]}.img")
        cmd = (
            f"dd if=/dev/zero of={loop_file} bs={blocksize} "
            f"count={int(size / blocksize)}"
        )
        if process.system(cmd, ignore_status=True, sudo=True) != 0:
            raise DiskError("Unable to create backing file for loop device")

        cmd = f"losetup {loop} {loop_file} -P"
        if process.system(cmd, ignore_status=True, sudo=True) != 0:
            raise DiskError("Unable to create the loop device")
        return loop

    def delete_loop_device(self, loop_device):
        """
        Deletes the specified loop device.

        :return: True if deleted.
        :rtype: bool
        """
        cmd = "losetup -aJl"
        loop_dic = json.loads(
            process.run(cmd, ignore_status=True, sudo=True).stdout_text
        )
        loop_file = ""
        for loop_dev in loop_dic["loopdevices"]:
            if loop_device == loop_dev["name"]:
                loop_file = loop_dev["back-file"]
        if not loop_file:
            raise DiskError("Unable to find backing file for loop device")
        cmd = f"losetup -d {loop_device}"
        if process.system(cmd, ignore_status=True, sudo=True) != 0:
            raise DiskError("Unable to delete the loop device")
        os.remove(loop_file)
        return True

    def get_disks(self):
        """
        Returns the physical "hard drives" available on this system

        This is a simple wrapper around `lsblk` and will return all the
        top level physical (non-virtual) devices return by it.

        TODO: this is currently Linux specific.  Support for other
        platforms is desirable and may be implemented in the future.

        :returns: a list of paths to the physical disks on the system
        :rtype: list of str
        """
        try:
            json_result = process.run("lsblk --json --paths --inverse")
        except process.CmdError as ce:
            raise DiskError(f"Error occurred while executing lsblk command: {ce}")
        try:
            json_data = json.loads(json_result.stdout_text)
        except json.JSONDecodeError as je:
            raise DiskError(f"Error occurred while parsing JSON data: {je}")
        disks = []
        for device in json_data["blockdevices"]:
            disks.append(device["name"])
            if "children" in device:
                for child in device["children"]:
                    disks.append(child["name"])
        return disks

    def get_all_disk_paths(self):
        """
        Returns all available disk names and alias on this  system

        This will get all the sysfs disks name entries by its device
        node name, by-uuid, by-id and by-path, irrespective of any
        platform and device type

        :returns: a list of all disk path names
        :rtype: list of str
        """
        disk_list = abs_path = []
        for path in [
            "/dev",
            "/dev/mapper",
            "/dev/disk/by-id",
            "/dev/disk/by-path",
            "/dev/disk/by-uuid",
            "/dev/disk/by-partuuid",
            "/dev/disk/by-partlabel",
        ]:
            if os.path.exists(path):
                for device in os.listdir(path):
                    abs_path.append(os.path.join(path, device))
                disk_list.extend(abs_path)
        return disk_list

    def get_absolute_disk_path(self):
        """
        Returns absolute device path of given disk

        This will get actual disks path of given device, it can take
        node name, by-uuid, by-id and by-path, irrespective of any
        platform and device type

        :param device: disk name or disk alias names sda or scsi-xxx
        :type device: str

        :returns: the device absolute path name
        :rtype: bool
        """
        if not os.path.exists(self.disk):
            for dev_path in self.get_all_disk_paths():
                if self.disk == os.path.basename(dev_path):
                    return dev_path
        return self.disk

    def get_available_filesystems(self):
        """
        Return a list of all available filesystem types

        :returns: a list of filesystem types
        :rtype: list of str
        """
        filesystems = set()
        with open("/proc/filesystems") as proc_fs:  # pylint: disable=W1514
            for proc_fs_line in proc_fs.readlines():
                filesystems.add(re.sub(r"(nodev)?\s*", "", proc_fs_line))
        return list(filesystems)

    def get_filesystem_type(self):
        """
        Returns the type of the filesystem of mount point informed.
        The default mount point considered when none is informed
        is the root "/" mount point.

        :param str mount_point: mount point to asses the filesystem type.
                                Default "/"

        :returns: filesystem type
        :rtype: str
        """
        if self.mount_point is None or self.is_dir_mounted() is False:
            self.mount_point = "/"
        with open("/proc/mounts") as mounts:  # pylint: disable=W1514
            for mount_line in mounts.readlines():
                _, fs_file, fs_vfstype, _, _, _ = mount_line.split()
                if fs_file == self.mount_point:
                    return fs_vfstype

    def is_root_device(self):
        """
        check for root disk

        :param device: device to check

        :returns: True or False, True if given device is root disk
                  otherwise will return False.
        """
        cmd = "lsblk --j -o MOUNTPOINT,PKNAME"
        output = process.run(cmd)
        result = json.loads(output.stdout_text)
        for item in result["blockdevices"]:
            if item["mountpoint"] == "/" and self.disk == str(item["pkname"]):
                return True
        return False

    def is_disk_mounted(self):
        """
        check if given disk is mounted or not

        :param device: disk/device name
        :type device: str

        :returns: True if the device/disk is mounted else False
        :rtype: bool
        """
        with open("/proc/mounts") as mounts:  # pylint: disable=W1514
            for mount_line in mounts.readlines():
                dev, _, _, _, _, _ = mount_line.split()
                if dev == self.disk:
                    return True
            return False

    def is_dir_mounted(self):
        """
        check if given directory is mounted or not

        :param dir_path: directory path
        :type dir_path: str

        :returns: True if the given director is mounted else False
        :rtype: bool
        """
        with open("/proc/mounts") as mounts:  # pylint: disable=W1514
            for mount_line in mounts.readlines():
                _, fs_dir, _, _, _, _ = mount_line.split()
                if fs_dir == self.mount_point:
                    return True
            return False

    def fs_exists(self):
        """
        check if filesystem exists on give disk/device

        :param device: disk/device name
        :type device: str

        :returns: returns True if filesystem exists on the give disk else False
        :rtype: bool
        """
        cmd = f"blkid -o value -s TYPE {self.disk}"
        out = process.system_output(cmd, shell=True, ignore_status=True).decode("utf-8")
        fs_list = ["ext2", "ext3", "ext4", "xfs", "btrfs"]
        if out in fs_list:
            return True
        return False

    def get_dir_mountpoint(self):
        """
        get mounted disk name that is mounted on given dir_path

        :param dir_path: absolute directory path
        :type dir_path: str

        :returns: returns disk name which mounted on given dir_path
        :rtype: str
        """
        with open("/proc/mounts") as mounts:  # pylint: disable=W1514
            for mount_line in mounts.readlines():
                dev, fs_dir, _, _, _, _ = mount_line.split()
                if fs_dir == self.mount_point:
                    return dev
            return None

    def get_disk_mountpoint(self):
        """
        get mountpoint on which given disk is mounted

        :param device: disk/device name
        :type device: str

        :return: return directory name on which disk is mounted
        :rtype: str
        """
        with open("/proc/mounts") as mounts:  # pylint: disable=W1514
            for mount_line in mounts.readlines():
                dev, fs_dir, _, _, _, _ = mount_line.split()
                if dev == self.disk:
                    return fs_dir
            return None

    def create_linux_raw_partition(self, size=None, num_of_par=1):
        """
        Creates partitions using sfdisk command

        :param disk_name: disk/device name
        :type disk_name: str
        :param size: size of partition
        :type size: str
        :param num_of_par: Number of partitions to be created
        :type num_of_par: int

        Returns list of created partitions
        """
        if not size:
            size = self.get_size_of_disk() / 1073741824
            size = size / num_of_par
            size = str(size) + "G"
        partitions = [
            "size= +" + size if val != 3 else "type=5"
            for val in range(0, num_of_par + 1)
        ]
        disk_partition_file = (
            "/tmp/creat_partition"
            + process.run("date '+%d-%m-%y_%T'").stdout_text.strip()
        )
        if not os.path.isfile(disk_partition_file):
            process.run("touch " + disk_partition_file)
        for line in partitions:
            genio.append_one_line(disk_partition_file, line)
        try:
            cmd = "sfdisk " + self.disk + " < " + disk_partition_file
            part_output = process.getoutput(cmd)
        except process.CmdError as ce:
            msg = f"sfdisk partition creation command failed on disk {self.disk}"
            LOGGER.warning(msg)
            raise DiskError(ce)
        self.rescan_disk()
        if "The partition table has been altered" in part_output:
            return self.get_disk_partitions()

    def get_size_of_disk(self):
        """
        Returns size of disk in bytes

        :param disk: disk/device name
        :type disk: str

        Return Type: int
        """
        return int(process.getoutput("lsblk -b --output SIZE -n -d " + self.disk))

    def delete_partition(self, partition_name):
        """
        Deletes mentioned partition from disk

        :param partition_name: partition absolute path
        :type partition_name: str
        """
        disk_index = re.search(r"\d+", partition_name).start()
        try:
            process.run(
                "sfdisk --delete "
                + partition_name[:disk_index]
                + " "
                + partition_name[disk_index:]
            )
        except process.CmdError as ce:
            msg = f"sfdisk --delete command failed on disk {partition_name}"
            LOGGER.warning(msg)
            raise DiskError(ce)

    def clean_disk(self):
        """
        Cleans partitions table of a disk

        :param disk_name: disk name
        :type disk_name: str
        """
        output = process.getoutput("sfdisk --delete " + self.disk)
        self.rescan_disk()
        if not self.get_disk_partitions():
            if "The partition table has been altered" in output:
                process.run("wipefs -af " + self.disk)

    def rescan_disk(self):
        """
        Rescans disk

        :param disk_name: disk name
        :type disk_name: str
        """
        self.disk = os.path.realpath(self.disk)
        if re.search(r"dm-\d+", self.disk):
            mpath_dict = multipath.get_multipath_details()
            for _ in range(len(mpath_dict["maps"])):
                if mpath_dict["maps"][_]["sysfs"] == self.disk.split("/")[-1]:
                    self.disk = (
                        "/dev/"
                        + mpath_dict["maps"][_]["path_groups"][0]["paths"][0]["dev"]
                    )
                    break
        process.run(f"echo 1 > /sys/block/{self.disk}/device/rescan")

    def get_disk_partitions(self):
        """
        Returns partitions of a disk excluding extended partition

        :param disk: disk name
        :type disk: str

        Returns array with all partitions of disk
        """
        self.rescan_disk()
        partitions_op = process.getoutput("sfdisk -l " + self.disk)
        return [
            line.split(" ")[0]
            for line in partitions_op.split("\n")
            if line.startswith(self.disk) and "Extended" not in line
        ]

    def get_io_scheduler_list(self):
        """
        Returns io scheduler available for the IO Device
        :param device_name: Device  name example like sda
        :return: list of IO scheduler
        """
        names = open(self.__sched_path(), "r", encoding="utf-8").read()
        return names.translate(str.maketrans("[]", " ")).split()

    def get_io_scheduler(self):
        """
        Return io scheduler name which is set currently  for device
        :param device_name: Device  name example like sda
        :return: IO scheduler
        :rtype :  str
        """
        return re.split(
            r"[\[\]]", open(self.__sched_path(), "r", encoding="utf-8").read()
        )[1]

    def __sched_path(self):

        file_path = f"/sys/block/{self.disk}/queue/scheduler"
        return file_path

    def set_io_scheduler(self, name):
        """
        Set io scheduler to a device
        :param device_name:  Device  name example like sda
        :param name: io scheduler name
        """
        if name not in self.get_io_scheduler_list():
            raise DiskError(f"No such IO scheduler: {name}")

        with open(self.__sched_path(), "w", encoding="utf-8") as fp:
            fp.write(name)
