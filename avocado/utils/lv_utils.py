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
# Author: Harish <harisrir@linux.vnet.ibm.com>
# Copyright: 2016 IBM
#
# Based on the code by
# Author: Plamen Dimitrov
# Copyright: Intra2net AG 2012

"""
Utility for taking shapshots from existing Logical volumes
or creates such.

:param vg_name: Name of the volume group.
:param lv_name: Name of the logical volume.
:param lv_size: Size of the logical volume as string in the form "#G"
        (for example 30G).
:param lv_snapshot_name: Name of the snapshot with origin the logical
        volume.
:param lv_snapshot_size: Size of the snapshot with origin the logical
        volume also as "#G".
:param ramdisk_vg_size: Size of the ramdisk virtual group.
:param ramdisk_basedir: Base directory for the ramdisk sparse file.
:param ramdisk_sparse_filename: Name of the ramdisk sparse file.
:param disk: Name of the disk to create volume group. If not provided,
             creates loop disk and creates volume group on it.

Sample ramdisk params:
- ramdisk_vg_size = "40000"
- ramdisk_basedir = "/tmp"
- ramdisk_sparse_filename = "virtual_hdd"

Sample general params:
- vg_name='autotest_vg',
- lv_name='autotest_lv',
- lv_size='1G',
- lv_snapshot_name='autotest_sn',
- lv_snapshot_size='1G'
The ramdisk volume group size is in MB.
"""

import logging
import os
import re
import shutil
import time
from . import process

LOGGER = logging.getLogger('avocado.test')


def get_diskspace(disk):
    """
    Get the entire disk space of a given disk
    :return: size in bytes
    """

    result = process.system_output('fdisk -l %s' % disk, shell=True)
    results = result.splitlines()
    for line in results:
        if line.startswith('Disk ' + disk):
            pattern = re.compile(r", (.*?) bytes")
            space = pattern.findall(line)[0]
    return space


def vg_ramdisk(disk, vg_name, ramdisk_vg_size,
               ramdisk_basedir, ramdisk_sparse_filename):
    """
    Create vg on top of ram memory to speed up lv performance.
    """
    vg_size = ramdisk_vg_size
    vg_ramdisk_dir = os.path.join(ramdisk_basedir, vg_name)
    ramdisk_filename = os.path.join(vg_ramdisk_dir,
                                    ramdisk_sparse_filename)
    vg_ramdisk_cleanup(ramdisk_filename, vg_ramdisk_dir, vg_name)
    result = ""
    if not os.path.exists(vg_ramdisk_dir):
        os.mkdir(vg_ramdisk_dir)
    try:
        LOGGER.debug("Mounting tmpfs")
        result = process.run("mount -t tmpfs tmpfs %s" %
                             vg_ramdisk_dir, shell=True)

        LOGGER.debug("Converting and copying /dev/zero")
        if disk:
            vg_size = get_diskspace(disk)
        cmd = ("dd if=/dev/zero of=%s bs=1M count=1 seek=%s" %
               (ramdisk_filename, vg_size))
        result = process.run(cmd, shell=True)
        if not disk:
            LOGGER.debug("Finding free loop device")
            result = process.run("losetup --find", shell=True)
    except process.CmdError, ex:
        LOGGER.error(ex)
        vg_ramdisk_cleanup(ramdisk_filename, vg_ramdisk_dir, vg_name)
        raise ex

    if not disk:
        loop_device = result.stdout.rstrip()
    else:
        loop_device = disk
    try:
        if not disk:
            LOGGER.debug("Creating loop device")
            result = process.run("losetup %s %s" %
                                 (loop_device, ramdisk_filename), shell=True)
        LOGGER.debug("Creating physical volume %s", loop_device)
        result = process.run("pvcreate %s" % loop_device, shell=True)
        LOGGER.debug("Creating volume group %s", vg_name)
        result = process.run("vgcreate %s %s" %
                             (vg_name, loop_device), shell=True)
    except process.CmdError, ex:
        LOGGER.error(ex)
        vg_ramdisk_cleanup(ramdisk_filename, vg_ramdisk_dir,
                           vg_name, loop_device)
        raise ex

    LOGGER.debug(result.stdout.rstrip())


def vg_ramdisk_cleanup(ramdisk_filename=None, vg_ramdisk_dir=None,
                       vg_name=None, loop_device=None):
    """
    Inline cleanup function in case of test error.
    """
    if vg_name is not None:
        loop_device = re.search(r"([/w]+) %s lvm2" % vg_name,
                                process.run("pvs").stdout)
        if loop_device is not None:
            loop_device = loop_device.group(1)
        result = process.run("vgremove %s" %
                             vg_name, ignore_status=True, shell=True)
        if result.exit_status == 0:
            LOGGER.debug(result.stdout.rstrip())
        else:
            LOGGER.debug("%s -> %s", result.command, result.stderr)

    if loop_device is not None:
        result = process.run("pvremove %s" % loop_device,
                             ignore_status=True, shell=True)
        if result.exit_status == 0:
            LOGGER.debug(result.stdout.rstrip())
        else:
            LOGGER.debug("%s -> %s", result.command, result.stderr)

        if loop_device in process.run("losetup --all").stdout:
            ramdisk_filename = re.search(r"%s: [d+]:d+ (([/w]+))" %
                                         loop_device,
                                         process.run("losetup --all").stdout)
            if ramdisk_filename is not None:
                ramdisk_filename = ramdisk_filename.group(1)

            for _ in range(10):
                time.sleep(0.1)
                result = process.run("losetup -d %s" % loop_device,
                                     ignore_status=True, shell=True)
                if "resource busy" not in result.stderr:
                    if result.exit_status == 0:
                        LOGGER.debug("Loop device %s deleted", loop_device)
                    else:
                        LOGGER.debug(
                            "%s -> %s", result.command, result.stderr)
                    break

    if ramdisk_filename is not None:
        if os.path.exists(ramdisk_filename):
            os.unlink(ramdisk_filename)
            LOGGER.debug("Ramdisk filename %s deleted", ramdisk_filename)
            vg_ramdisk_dir = os.path.dirname(ramdisk_filename)

    if vg_ramdisk_dir is not None:
        process.run("umount %s" % vg_ramdisk_dir,
                    ignore_status=True, shell=True)
        if result.exit_status == 0:
            LOGGER.debug("Successfully unmounted tmpfs from %s",
                         vg_ramdisk_dir)
        else:
            LOGGER.debug("%s -> %s", result.command, result.stderr)

        if os.path.exists(vg_ramdisk_dir):
            try:
                shutil.rmtree(vg_ramdisk_dir)
                LOGGER.debug("Ramdisk directory %s deleted", vg_ramdisk_dir)
            except OSError:
                pass


def vg_check(vg_name):
    """
    Check whether provided volume group exists.
    """
    cmd = "vgdisplay %s" % vg_name
    try:
        process.run(cmd, shell=True)
        LOGGER.debug("Provided volume group exists: %s", vg_name)
        return True
    except process.CmdError, exception:
        LOGGER.error(exception)
        return False


def vg_list():
    """
    List available volume groups.
    """
    cmd = "vgs --all"
    vgroups = {}
    result = process.run(cmd, shell=True)
    lines = result.stdout.strip().splitlines()
    if len(lines) > 1:
        columns = lines[0].split()
        lines = lines[1:]
    else:
        return vgroups

    for line in lines:
        details = line.split()
        details_dict = {}
        index = 0
        for column in columns:
            if re.search("VG", column):
                vg_name = details[index]
            else:
                details_dict[column] = details[index]
            index += 1
        vgroups[vg_name] = details_dict
    return vgroups


def vg_create(vg_name, pv_list, force=False):
    """
    Create a volume group by using the block special devices
    """

    if vg_check(vg_name):
        raise Exception("Volume group '%s' already exist" % vg_name)
    if force:
        cmd = "vgcreate -f"
    else:
        cmd = "vgcreate"
    cmd += " %s %s" % (vg_name, pv_list)
    result = process.run(cmd, shell=True)
    LOGGER.debug(result.stdout.rstrip())


def vg_remove(vg_name):
    """
    Remove a volume group.
    """

    if not vg_check(vg_name):
        raise Exception("Volume group '%s' could not be found" % vg_name)
    cmd = "vgremove -f %s" % vg_name
    result = process.run(cmd, shell=True)
    LOGGER.debug(result.stdout.rstrip())


def lv_check(vg_name, lv_name):
    """
    Check whether provided Logical volume exists.
    """
    cmd = "lvdisplay"
    result = process.run(cmd, ignore_status=True, shell=True)

    lvpattern = r"LV Path\s+/dev/%s/%s\s+" % (vg_name, lv_name)
    match = re.search(lvpattern, result.stdout.rstrip())
    if match:
        LOGGER.debug("Provided Logical volume %s exists in %s",
                     lv_name, vg_name)
        return True
    else:
        return False


def lv_remove(vg_name, lv_name):
    """
    Remove a logical volume.
    """

    if not vg_check(vg_name):
        raise Exception("Volume group could not be found")
    if not lv_check(vg_name, lv_name):
        raise Exception("Logical volume could not be found")

    cmd = "lvremove -f %s/%s" % (vg_name, lv_name)
    result = process.run(cmd, shell=True)
    LOGGER.debug(result.stdout.rstrip())


def lv_create(vg_name, lv_name, lv_size, force_flag=True):
    """
    Create a Logical volume in a volume group.

    The volume group must already exist.
    """

    if not vg_check(vg_name):
        raise Exception("Volume group could not be found")
    if lv_check(vg_name, lv_name) and not force_flag:
        raise Exception("Logical volume already exists")
    elif lv_check(vg_name, lv_name) and force_flag:
        lv_remove(vg_name, lv_name)

    cmd = "lvcreate --size %s --name %s %s" % (lv_size, lv_name, vg_name)
    result = process.run(cmd, shell=True)
    LOGGER.debug(result.stdout.rstrip())


def lv_list():
    """
    List available group volumes.
    """
    cmd = "lvs --all"
    volumes = {}
    result = process.run(cmd, shell=True)

    lines = result.stdout.strip().splitlines()
    if len(lines) > 1:
        lines = lines[1:]
    else:
        return volumes

    for line in lines:
        details = line.split()
        length = len(details)
        details_dict = {}
        lv_name = details[0]
        details_dict["VG"] = details[1]
        details_dict["Attr"] = details[2]
        details_dict["LSize"] = details[3]
        if length == 5:
            details_dict["Origin_Data"] = details[4]
        elif length > 5:
            details_dict["Origin_Data"] = details[5]
            details_dict["Pool"] = details[4]
        volumes[lv_name] = details_dict
    return volumes


def thin_lv_create(vg_name, thinpool_name="lvthinpool", thinpool_size="1.5G",
                   thinlv_name="lvthin", thinlv_size="1G"):
    """
    Create a thin volume from given volume group.

    :param vg_name: An exist volume group
    :param thinpool_name: The name of thin pool
    :param thinpool_size: The size of thin pool to be created
    :param thinlv_name: The name of thin volume
    :param thinlv_size: The size of thin volume
    """
    tp_cmd = "lvcreate --thinpool %s --size %s %s" % (thinpool_name,
                                                      thinpool_size,
                                                      vg_name)
    try:
        process.run(tp_cmd, shell=True)
    except process.CmdError, detail:
        LOGGER.debug(detail)
        raise Exception("Create thin volume pool failed.")
    LOGGER.debug("Created thin volume pool: %s", thinpool_name)
    lv_cmd = ("lvcreate --name %s --virtualsize %s "
              "--thin %s/%s" % (thinlv_name, thinlv_size,
                                vg_name, thinpool_name))
    try:
        process.run(lv_cmd, shell=True)
    except process.CmdError, detail:
        LOGGER.error(detail)
        raise Exception("Create thin volume failed.")
    LOGGER.debug("Created thin volume:%s", thinlv_name)
    return (thinpool_name, thinlv_name)


def lv_take_snapshot(vg_name, lv_name,
                     lv_snapshot_name, lv_snapshot_size):
    """
    Take a snapshot of the original Logical volume.
    """

    if not vg_check(vg_name):
        raise Exception("Volume group could not be found")
    if lv_check(vg_name, lv_snapshot_name):
        raise Exception("Snapshot already exists")
    if not lv_check(vg_name, lv_name):
        raise Exception("Snapshot's origin could not be found")

    cmd = ("lvcreate --size %s --snapshot --name %s /dev/%s/%s" %
           (lv_snapshot_size, lv_snapshot_name, vg_name, lv_name))
    try:
        result = process.run(cmd, shell=True)
    except process.CmdError, ex:
        if ('Logical volume "%s" already exists in volume group "%s"' %
            (lv_snapshot_name, vg_name) in ex.result_obj.stderr and
            re.search(re.escape(lv_snapshot_name + " [active]"),
                      process.run("lvdisplay").stdout)):
            # the above conditions detect if merge of snapshot was postponed
            LOGGER.debug(("Logical volume %s is still active! " +
                          "Attempting to deactivate..."), lv_name)
            lv_reactivate(vg_name, lv_name)
            result = process.run(cmd, shell=True)
        else:
            raise ex
    LOGGER.info(result.stdout.rstrip())


def lv_revert(vg_name, lv_name, lv_snapshot_name):
    """
    Revert the origin to a snapshot.
    """
    try:
        if not vg_check(vg_name):
            raise Exception("Volume group could not be found")
        if not lv_check(vg_name, lv_snapshot_name):
            raise Exception("Snapshot could not be found")
        if (not lv_check(vg_name, lv_snapshot_name) and not lv_check(vg_name,
                                                                     lv_name)):
            raise Exception("Snapshot and its origin could not be found")
        if (lv_check(vg_name, lv_snapshot_name) and not lv_check(vg_name,
                                                                 lv_name)):
            raise Exception("Snapshot origin could not be found")

        cmd = ("lvconvert --merge /dev/%s/%s" % (vg_name, lv_snapshot_name))
        result = process.run(cmd, shell=True)
        if (("Merging of snapshot %s will start next activation." %
             lv_snapshot_name) in result.stdout):
            raise Exception("The Logical volume %s is still active" %
                            lv_name)
        result = result.stdout.rstrip()

    except Exception, ex:
        # detect if merge of snapshot was postponed
        # and attempt to reactivate the volume.
        active_lv_pattern = re.escape("%s [active]" % lv_snapshot_name)
        lvdisplay_output = process.run("lvdisplay").stdout
        if ('Snapshot could not be found' in ex and
                re.search(active_lv_pattern, lvdisplay_output) or
                "The Logical volume %s is still active" % lv_name in ex):
            LOGGER.debug(("Logical volume %s is still active! " +
                          "Attempting to deactivate..."), lv_name)
            lv_reactivate(vg_name, lv_name)
            result = "Continuing after reactivation"
        elif 'Snapshot could not be found' in ex:
            LOGGER.error(ex)
            result = "Could not revert to snapshot"
        else:
            raise ex
    LOGGER.debug(result)


def lv_revert_with_snapshot(vg_name, lv_name,
                            lv_snapshot_name, lv_snapshot_size):
    """
    Perform Logical volume merge with snapshot and take a new snapshot.
    """

    lv_revert(vg_name, lv_name, lv_snapshot_name)
    lv_take_snapshot(vg_name, lv_name, lv_snapshot_name, lv_snapshot_size)


def lv_reactivate(vg_name, lv_name, timeout=10):
    """
    In case of unclean shutdowns some of the lvs is still active and merging
    is postponed. Use this function to attempt to deactivate and reactivate
    all of them to cause the merge to happen.
    """
    try:
        process.run("lvchange -an /dev/%s/%s" % (vg_name, lv_name), shell=True)
        time.sleep(timeout)
        process.run("lvchange -ay /dev/%s/%s" % (vg_name, lv_name), shell=True)
        time.sleep(timeout)
    except process.CmdError:
        LOGGER.error(("Failed to reactivate %s - please, " +
                      "nuke the process that uses it first."), lv_name)
        raise Exception("The Logical volume %s is still active" % lv_name)


def lv_mount(vg_name, lv_name, mount_loc, create_filesystem=""):
    """
    Mount a Logical volume to a mount location.

    The create_filesystem can be one of ext2, ext3, ext4, vfat or empty
    if the filesystem was already created and the mkfs process is skipped.
    """

    try:
        if create_filesystem:
            result = process.run("mkfs.%s /dev/%s/%s" %
                                 (create_filesystem, vg_name, lv_name),
                                 shell=True)
            LOGGER.debug(result.stdout.rstrip())
        result = process.run("mount /dev/%s/%s %s" %
                             (vg_name, lv_name, mount_loc), shell=True)
    except process.CmdError, ex:
        LOGGER.error(ex)
        return False
    return True


def lv_umount(vg_name, lv_name):
    """
    Unmount a Logical volume from a mount location.
    """

    try:
        process.run("umount /dev/%s/%s" % (vg_name, lv_name), shell=True)
    except process.CmdError, ex:
        LOGGER.error(ex)
        return False
    return True
