# Copyright (C) IBM 2016 - Harish <harisrir@linux.vnet.ibm.com>
# Copyright (C) Red Hat 2016 - Lukas Doktor <ldoktor@redhat.com>
#
# Based on code by
# Copyright (C) Intra2net AG 2012 - Plamen Dimitrov
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; version 2.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
# for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Source: https://github.com/autotest/autotest/blob/master/client/lv_utils.py


import logging
import os
import re
import shutil
import time
from . import process


LOGGER = logging.getLogger('avocado.test')


class LVException(Exception):
    """
    Base Exception Class for all exceptions
    """
    pass


def get_diskspace(disk):
    """
    Get the entire disk space of a given disk

    :param disk: Name of the disk to find free space
    :return: size in bytes
    """
    result = process.system_output(
        'fdisk -l %s' % disk, env={"LANG": "C"}, sudo=True)
    results = result.splitlines()
    for line in results:
        if line.startswith('Disk ' + disk):
            return re.findall(r", (.*?) bytes", line)[0]
    raise LVException('Error in finding disk space')


def vg_ramdisk(disk, vg_name, ramdisk_vg_size,
               ramdisk_basedir, ramdisk_sparse_filename):
    """
    Create vg on top of ram memory to speed up lv performance.
    When disk is specified size of the physical volume is taken from
    existing disk space.

    :param disk: Name of the disk in which volume groups are created.
    :param vg_name: Name of the volume group.
    :param ramdisk_vg_size: Size of the ramdisk virtual group (MB).
    :param ramdisk_basedir: Base directory for the ramdisk sparse file.
    :param ramdisk_sparse_filename: Name of the ramdisk sparse file.
    :return: ramdisk_filename, vg_ramdisk_dir, vg_name, loop_device
    :raise LVException: On failure

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
    vg_size = ramdisk_vg_size
    vg_ramdisk_dir = os.path.join(ramdisk_basedir, vg_name)
    ramdisk_filename = os.path.join(vg_ramdisk_dir,
                                    ramdisk_sparse_filename)
    # Try to cleanup the ramdisk before defining it
    try:
        vg_ramdisk_cleanup(ramdisk_filename, vg_ramdisk_dir, vg_name)
    except LVException:
        pass
    if not os.path.exists(vg_ramdisk_dir):
        os.makedirs(vg_ramdisk_dir)
    try:
        LOGGER.debug("Mounting tmpfs")
        process.run("mount -t tmpfs tmpfs %s" %
                    vg_ramdisk_dir, sudo=True)

        LOGGER.debug("Converting and copying /dev/zero")
        if disk:
            vg_size = get_diskspace(disk)

        # Initializing sparse file with extra few bytes
        cmd = ("dd if=/dev/zero of=%s bs=1M count=1 seek=%s" %
               (ramdisk_filename, vg_size))
        process.run(cmd)
        if not disk:
            LOGGER.debug("Finding free loop device")
            result = process.run("losetup --find", sudo=True)
    except process.CmdError as ex:
        LOGGER.error(ex)
        vg_ramdisk_cleanup(ramdisk_filename, vg_ramdisk_dir, vg_name)
        raise LVException("Fail to create vg_ramdisk: %s" % ex)

    if not disk:
        loop_device = result.stdout.rstrip()
    else:
        loop_device = disk
    try:
        if not disk:
            LOGGER.debug("Creating loop device")
            process.run("losetup %s %s" %
                        (loop_device, ramdisk_filename), sudo=True)
        LOGGER.debug("Creating physical volume %s", loop_device)
        process.run("pvcreate -y %s" % loop_device, sudo=True)
        LOGGER.debug("Creating volume group %s", vg_name)
        process.run("vgcreate %s %s" %
                    (vg_name, loop_device), sudo=True)
    except process.CmdError as ex:
        LOGGER.error(ex)
        vg_ramdisk_cleanup(ramdisk_filename, vg_ramdisk_dir,
                           vg_name, loop_device)
        raise LVException("Fail to create vg_ramdisk: %s" % ex)
    return ramdisk_filename, vg_ramdisk_dir, vg_name, loop_device


def vg_ramdisk_cleanup(ramdisk_filename=None, vg_ramdisk_dir=None,
                       vg_name=None, loop_device=None):
    """
    Inline cleanup function in case of test error.

    It detects whether the components were initialized and if so it tries
    to remove them. In case of failure it raises summary exception.

    :param ramdisk_filename: Name of the ramdisk sparse file.
    :param vg_ramdisk_dir: Location of the ramdisk file
    :vg_name: Name of the volume group
    :loop_device: Name of the disk or loop device
    :raise LVException: In case it fail to clean things detected in system
    """
    errs = []
    if vg_name is not None:
        loop_device = re.search(r"([/\w-]+) +%s +lvm2" % vg_name,
                                process.run("pvs", sudo=True).stdout)
        if loop_device is not None:
            loop_device = loop_device.group(1)
        process.run("vgremove -f %s" %
                    vg_name, ignore_status=True, sudo=True)

    if loop_device is not None:
        result = process.run("pvremove %s" % loop_device,
                             ignore_status=True, sudo=True)
        if result.exit_status != 0:
            errs.append("wipe pv")
            LOGGER.error("Failed to wipe pv from %s: %s", loop_device, result)

        if loop_device in process.run("losetup --all").stdout:
            ramdisk_filename = re.search(r"%s: \[\d+\]:\d+ \(([/\w]+)\)" %
                                         loop_device,
                                         process.run("losetup --all").stdout)
            if ramdisk_filename is not None:
                ramdisk_filename = ramdisk_filename.group(1)

            for _ in xrange(10):
                result = process.run("losetup -d %s" % loop_device,
                                     ignore_status=True, sudo=True)
                if "resource busy" not in result.stderr:
                    if result.exit_status != 0:
                        errs.append("remove loop device")
                        LOGGER.error("Unexpected failure when removing loop"
                                     "device %s, check the log", loop_device)
                    break
                time.sleep(0.1)

    if ramdisk_filename is not None:
        if os.path.exists(ramdisk_filename):
            os.unlink(ramdisk_filename)
            LOGGER.debug("Ramdisk filename %s deleted", ramdisk_filename)
            vg_ramdisk_dir = os.path.dirname(ramdisk_filename)

    if vg_ramdisk_dir is not None:
        if not process.system("mountpoint %s" % vg_ramdisk_dir,
                              ignore_status=True):
            for _ in xrange(10):
                result = process.run("umount %s" % vg_ramdisk_dir,
                                     ignore_status=True, sudo=True)
                time.sleep(0.1)
                if result.exit_status == 0:
                    break
            else:
                errs.append("umount")
                LOGGER.error("Unexpected failure unmounting %s, check the "
                             "log", vg_ramdisk_dir)

        if os.path.exists(vg_ramdisk_dir):
            try:
                shutil.rmtree(vg_ramdisk_dir)
                LOGGER.debug("Ramdisk directory %s deleted", vg_ramdisk_dir)
            except OSError as details:
                errs.append("rm-ramdisk-dir")
                LOGGER.error("Failed to remove ramdisk_dir: %s", details)
    if errs:
        raise LVException("vg_ramdisk_cleanup failed: %s" % ", ".join(errs))


def vg_check(vg_name):
    """
    Check whether provided volume group exists.

    :param vg_name: Name of the volume group.
    """
    cmd = "vgdisplay %s" % vg_name
    try:
        process.run(cmd, sudo=True)
        LOGGER.debug("Provided volume group exists: %s", vg_name)
        return True
    except process.CmdError as exception:
        LOGGER.error(exception)
        return False


def vg_list():
    """
    List available volume groups.

    :return List of volume groups.
    """
    cmd = "vgs --all"
    vgroups = {}
    result = process.run(cmd, sudo=True)
    lines = result.stdout.strip().splitlines()
    if len(lines) > 1:
        columns = lines[0].split()
        lines = lines[1:]
    else:
        return vgroups
    # TODO: Optimize this
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

    :param vg_name: Name of the volume group
    :param pv_list: List of physical volumes
    :param force: Create volume group forcefully
    """

    if vg_check(vg_name):
        raise LVException("Volume group '%s' already exist" % vg_name)
    if force:
        cmd = "vgcreate -f"
    else:
        cmd = "vgcreate"
    cmd += " %s %s" % (vg_name, pv_list)
    process.run(cmd, sudo=True)


def vg_remove(vg_name):
    """
    Remove a volume group.

    :param vg_name: Name of the volume group
    """

    if not vg_check(vg_name):
        raise LVException("Volume group '%s' could not be found" % vg_name)
    cmd = "vgremove -f %s" % vg_name
    process.run(cmd, sudo=True)


def lv_check(vg_name, lv_name):
    """
    Check whether provided Logical volume exists.

    :param vg_name: Name of the volume group
    :param lv_name: Name of the logical volume
    """
    cmd = "lvdisplay"
    result = process.run(cmd, ignore_status=True, sudo=True)

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

    :param vg_name: Name of the volume group
    :param lv_name: Name of the logical volume
    """

    if not vg_check(vg_name):
        raise LVException("Volume group could not be found")
    if not lv_check(vg_name, lv_name):
        raise LVException("Logical volume could not be found")

    cmd = "lvremove -f %s/%s" % (vg_name, lv_name)
    process.run(cmd, sudo=True)


def lv_create(vg_name, lv_name, lv_size, force_flag=True):
    """
    Create a Logical volume in a volume group.
    The volume group must already exist.

    :param vg_name: Name of the volume group
    :param lv_name: Name of the logical volume
    :param lv_size: Size for the logical volume to be created
    """

    if not vg_check(vg_name):
        raise LVException("Volume group could not be found")
    if lv_check(vg_name, lv_name) and not force_flag:
        raise LVException("Logical volume already exists")
    elif lv_check(vg_name, lv_name) and force_flag:
        lv_remove(vg_name, lv_name)

    cmd = "lvcreate --size %s --name %s %s -y" % (lv_size, lv_name, vg_name)
    process.run(cmd, sudo=True)


def lv_list():
    """
    List available group volumes.

    :return list available logical volumes
    """
    cmd = "lvs --all"
    volumes = {}
    result = process.run(cmd, sudo=True)

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
    tp_cmd = "lvcreate --thinpool %s --size %s %s -y" % (thinpool_name,
                                                         thinpool_size,
                                                         vg_name)
    try:
        process.run(tp_cmd, sudo=True)
    except process.CmdError as detail:
        LOGGER.debug(detail)
        raise LVException("Create thin volume pool failed.")
    LOGGER.debug("Created thin volume pool: %s", thinpool_name)
    lv_cmd = ("lvcreate --name %s --virtualsize %s "
              "--thin %s/%s -y" % (thinlv_name, thinlv_size,
                                   vg_name, thinpool_name))
    try:
        process.run(lv_cmd, sudo=True)
    except process.CmdError as detail:
        LOGGER.error(detail)
        raise LVException("Create thin volume failed.")
    LOGGER.debug("Created thin volume:%s", thinlv_name)
    return (thinpool_name, thinlv_name)


def lv_take_snapshot(vg_name, lv_name,
                     lv_snapshot_name, lv_snapshot_size):
    """
    Take a snapshot of the original Logical volume.

    :param vg_name: An existing volume group
    :param lv_name: An existing logical volume
    :param lv_snapshot_name: Name of the snapshot be to created
    :param lv_snapshot_size: Size of the snapshot
    """

    if not vg_check(vg_name):
        raise LVException("Volume group could not be found")
    if lv_check(vg_name, lv_snapshot_name):
        raise LVException("Snapshot already exists")
    if not lv_check(vg_name, lv_name):
        raise LVException("Snapshot's origin could not be found")

    cmd = ("lvcreate --size %s --snapshot --name %s /dev/%s/%s -y" %
           (lv_snapshot_size, lv_snapshot_name, vg_name, lv_name))
    try:
        process.run(cmd, sudo=True)
    except process.CmdError as ex:
        if ('Logical volume "%s" already exists in volume group "%s"'
            % (lv_snapshot_name, vg_name) in ex.result_obj.stderr and
            re.search(re.escape(lv_snapshot_name + " [active]"),
                      process.run("lvdisplay", sudo=True).stdout)):
            # the above conditions detect if merge of snapshot was postponed
            LOGGER.debug(("Logical volume %s is still active! " +
                          "Attempting to deactivate..."), lv_name)
            lv_reactivate(vg_name, lv_name)
            process.run(cmd, sudo=True)
        else:
            raise ex


def lv_revert(vg_name, lv_name, lv_snapshot_name):
    """
    Revert the origin to a snapshot.

    :param vg_name: An existing volume group
    :param lv_name: An existing logical volume
    :param lv_snapshot_name: Name of the snapshot be to reverted
    """
    try:
        if not vg_check(vg_name):
            raise LVException("Volume group could not be found")
        if not lv_check(vg_name, lv_snapshot_name):
            raise LVException("Snapshot could not be found")
        if (not lv_check(vg_name, lv_snapshot_name) and not lv_check(vg_name,
                                                                     lv_name)):
            raise LVException("Snapshot and its origin could not be found")
        if (lv_check(vg_name, lv_snapshot_name) and not lv_check(vg_name,
                                                                 lv_name)):
            raise LVException("Snapshot origin could not be found")

        cmd = ("lvconvert --merge /dev/%s/%s" % (vg_name, lv_snapshot_name))
        result = process.run(cmd, sudo=True)
        if (("Merging of snapshot %s will start next activation." %
             lv_snapshot_name) in result.stdout):
            raise LVException("The Logical volume %s is still active" %
                              lv_name)

    except process.CmdError as ex:
        # detect if merge of snapshot was postponed
        # and attempt to reactivate the volume.
        active_lv_pattern = re.escape("%s [active]" % lv_snapshot_name)
        lvdisplay_output = process.run("lvdisplay", sudo=True).stdout
        if ('Snapshot could not be found' in ex and
                re.search(active_lv_pattern, lvdisplay_output) or
                "The Logical volume %s is still active" % lv_name in ex):
            LOGGER.debug(("Logical volume %s is still active! " +
                          "Attempting to deactivate..."), lv_name)
            lv_reactivate(vg_name, lv_name)
            LOGGER.error("Continuing after reactivation")
        elif 'Snapshot could not be found' in ex:
            LOGGER.error(ex)
            LOGGER.error("Could not revert to snapshot")
        else:
            raise ex


def lv_revert_with_snapshot(vg_name, lv_name,
                            lv_snapshot_name, lv_snapshot_size):
    """
    Perform Logical volume merge with snapshot and take a new snapshot.

    :param vg_name: Name of volume group in which lv has to be reverted
    :param lv_name: Name of the logical volume to be reverted
    :param lv_snapshot_name: Name of the snapshot be to reverted
    :param lv_snapshot_size: Size of the snapshot
    """

    lv_revert(vg_name, lv_name, lv_snapshot_name)
    lv_take_snapshot(vg_name, lv_name, lv_snapshot_name, lv_snapshot_size)


def lv_reactivate(vg_name, lv_name, timeout=10):
    """
    In case of unclean shutdowns some of the lvs is still active and merging
    is postponed. Use this function to attempt to deactivate and reactivate
    all of them to cause the merge to happen.

    :param vg_name: Name of volume group
    :param lv_name: Name of the logical volume
    :param timeout: Timeout between operations
    """
    try:
        process.run("lvchange -an /dev/%s/%s" % (vg_name, lv_name), sudo=True)
        time.sleep(timeout)
        process.run("lvchange -ay /dev/%s/%s" % (vg_name, lv_name), sudo=True)
        time.sleep(timeout)
    except process.CmdError:
        LOGGER.error(("Failed to reactivate %s - please, " +
                      "nuke the process that uses it first."), lv_name)
        raise LVException("The Logical volume %s is still active" % lv_name)


def lv_mount(vg_name, lv_name, mount_loc, create_filesystem=""):
    """
    Mount a Logical volume to a mount location.

    :param vg_name: Name of volume group
    :param lv_name: Name of the logical volume
    :mount_loc: Location to mount the logical volume
    :param create_filesystem: Can be one of ext2, ext3, ext4, vfat or empty
                              if the filesystem was already created and the
                              mkfs process is skipped
    """

    try:
        if create_filesystem:
            process.run("mkfs.%s /dev/%s/%s" %
                        (create_filesystem, vg_name, lv_name),
                        sudo=True)
        process.run("mount /dev/%s/%s %s" %
                    (vg_name, lv_name, mount_loc), sudo=True)
    except process.CmdError as ex:
        raise LVException("Fail to mount lv: %s" % ex)


def lv_umount(vg_name, lv_name):
    """
    Unmount a Logical volume from a mount location.

    :param vg_name: Name of volume group
    :param lv_name: Name of the logical volume
    """

    try:
        process.run("umount /dev/%s/%s" % (vg_name, lv_name), sudo=True)
    except process.CmdError as ex:
        raise LVException("Fail to unmount lv: %s" % ex)
