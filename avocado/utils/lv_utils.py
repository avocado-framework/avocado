# Copyright (C) IBM 2016 - Harish <harisrir@linux.vnet.ibm.com>
# Copyright (C) Red Hat 2016 - Lukas Doktor <ldoktor@redhat.com>
# Copyright (C) Intra2net AG 2018 - Plamen Dimitrov <pdimitrov@pevogam.com>
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
import warnings

from avocado.utils import process

LOGGER = logging.getLogger(__name__)


class LVException(Exception):
    """
    Base Exception Class for all exceptions
    """


def get_diskspace(disk):
    """
    Get the entire disk space of a given disk.

    :param str disk: name of the disk to find the free space of
    :returns: size in bytes
    :rtype: str
    :raises: :py:class:`LVException` on failure to find disk space
    """
    warnings.warn("deprecated, use get_device_total_space instead",
                  DeprecationWarning)
    result = process.run(f'fdisk -l {disk}',
                         env={"LANG": "C"}, sudo=True).stdout_text
    results = result.splitlines()
    for line in results:
        if line.startswith('Disk ' + disk):
            return re.findall(r", (.*?) bytes", line)[0]
    raise LVException('Error in finding disk space')


def get_device_total_space(disk):
    """Get the total device size.

    :param str device: name of the device/disk to find the total size
    :returns: size in bytes
    :rtype: int
    :raises: :py:class:`LVException` on failure to find disk space
    """
    result = process.run(f'fdisk -l {disk}',
                         env={"LANG": "C"}, sudo=True).stdout_text
    results = result.splitlines()
    for line in results:
        if line.startswith('Disk ' + disk):
            return int(re.findall(r", (.*?) bytes", line)[0])
    raise LVException('Error in finding disk space')


def get_devices_total_space(devices):
    """Get the total size of given device(s)/disk(s).

    :param list devices: list with the names of devices separated with space.
    :returns: sizes in bytes
    :rtype: int
    :raises: :py:class:`LVException` on failure to find disk space
    """
    size = 0
    for device in devices:
        size = size + get_device_total_space(device)
    if not size:
        raise LVException('failed to get disks size')
    return size


def vg_ramdisk(disk, vg_name, ramdisk_vg_size,
               ramdisk_basedir, ramdisk_sparse_filename,
               use_tmpfs=True):
    """
    Create volume group on top of ram memory to speed up LV performance.
    When disk is specified the size of the physical volume is taken from
    existing disk space.

    :param str disk: name of the disk in which volume groups are created
    :param str vg_name: name of the volume group
    :param str ramdisk_vg_size: size of the ramdisk virtual group (MB)
    :param str ramdisk_basedir: base directory for the ramdisk sparse file
    :param str ramdisk_sparse_filename: name of the ramdisk sparse file
    :param bool use_tmpfs: whether to use RAM or slower storage
    :returns: ramdisk_filename, vg_ramdisk_dir, vg_name, loop_device
    :rtype: (str, str, str, str)
    :raises: :py:class:`LVException` on failure at any stage

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
    warnings.warn("deprecated, use existing methods: vg_create, lv_create",
                  DeprecationWarning)
    vg_size = ramdisk_vg_size
    vg_ramdisk_dir = os.path.join(ramdisk_basedir, vg_name)
    ramdisk_filename = os.path.join(vg_ramdisk_dir,
                                    ramdisk_sparse_filename)
    # Try to cleanup the ramdisk before defining it
    try:
        vg_ramdisk_cleanup(ramdisk_filename, vg_ramdisk_dir,
                           vg_name, use_tmpfs)
    except LVException:
        pass
    if not os.path.exists(vg_ramdisk_dir):
        os.makedirs(vg_ramdisk_dir)
    try:
        if use_tmpfs:
            LOGGER.debug("Mounting tmpfs")
            process.run(f"mount -t tmpfs tmpfs {vg_ramdisk_dir}",
                        sudo=True)

        LOGGER.debug("Converting and copying /dev/zero")
        if disk:
            vg_size = get_diskspace(disk)

        # Initializing sparse file with extra few bytes
        cmd = (f"dd if=/dev/zero of={ramdisk_filename} bs=1M count=1 "
               f"seek={vg_size}")
        process.run(cmd)
        if not disk:
            LOGGER.debug("Finding free loop device")
            result = process.run("losetup --find", sudo=True)
    except process.CmdError as ex:
        LOGGER.error(ex)
        vg_ramdisk_cleanup(ramdisk_filename, vg_ramdisk_dir,
                           vg_name, use_tmpfs)
        raise LVException(f"Fail to create vg_ramdisk: {ex}")

    if not disk:
        loop_device = result.stdout_text.rstrip()
    else:
        loop_device = disk
    try:
        if not disk:
            LOGGER.debug("Creating loop device")
            process.run(f"losetup {loop_device} {ramdisk_filename}",
                        sudo=True)
        LOGGER.debug("Creating physical volume %s", loop_device)
        process.run(f"pvcreate -y {loop_device}", sudo=True)
        LOGGER.debug("Creating volume group %s", vg_name)
        process.run(f"vgcreate {vg_name} {loop_device}", sudo=True)
    except process.CmdError as ex:
        LOGGER.error(ex)
        vg_ramdisk_cleanup(ramdisk_filename, vg_ramdisk_dir,
                           vg_name, loop_device, use_tmpfs)
        raise LVException(f"Fail to create vg_ramdisk: {ex}")
    return ramdisk_filename, vg_ramdisk_dir, vg_name, loop_device


def vg_ramdisk_cleanup(ramdisk_filename=None, vg_ramdisk_dir=None,
                       vg_name=None, loop_device=None, use_tmpfs=True):
    """
    Clean up any stage of the VG ramdisk setup in case of test error.

    This detects whether the components were initialized and if so tries
    to remove them. In case of failure it raises summary exception.

    :param str ramdisk_filename: name of the ramdisk sparse file
    :param str vg_ramdisk_dir: location of the ramdisk file
    :param str vg_name: name of the volume group
    :param str loop_device: name of the disk or loop device
    :param bool use_tmpfs: whether to use RAM or slower storage
    :returns: ramdisk_filename, vg_ramdisk_dir, vg_name, loop_device
    :rtype: (str, str, str, str)
    :raises: :py:class:`LVException` on intolerable failure at any stage
    """
    warnings.warn("deprecated, use existing methods: vg_remove, lv_remove",
                  DeprecationWarning)
    errs = []
    if vg_name is not None:
        loop_device = re.search(fr"([/\w-]+) +{vg_name} +lvm2",
                                process.run("pvs", sudo=True).stdout_text)
        if loop_device is not None:
            loop_device = loop_device.group(1)
        process.run(f"vgremove -f {vg_name}", ignore_status=True, sudo=True)

    if loop_device is not None:
        result = process.run(f"pvremove {loop_device}",
                             ignore_status=True, sudo=True)
        if result.exit_status != 0:
            errs.append("wipe pv")
            LOGGER.error("Failed to wipe pv from %s: %s", loop_device, result)

        losetup_all = process.run("losetup --all", sudo=True).stdout_text
        if loop_device in losetup_all:
            ramdisk_filename = re.search(r"%s: \[\d+\]:\d+ \(([/\w]+)\)" %  # pylint: disable=C0209
                                         loop_device, losetup_all)
            if ramdisk_filename is not None:
                ramdisk_filename = ramdisk_filename.group(1)

            for _ in range(10):
                result = process.run(f"losetup -d {loop_device}",
                                     ignore_status=True, sudo=True)
                if b"resource busy" not in result.stderr:
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
        if use_tmpfs and not process.system(f"mountpoint {vg_ramdisk_dir}",
                                            ignore_status=True):
            for _ in range(10):
                result = process.run(f"umount {vg_ramdisk_dir}",
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
        raise LVException(f"vg_ramdisk_cleanup failed: {', '.join(errs)}")


def vg_check(vg_name):
    """
    Check whether provided volume group exists.

    :param str vg_name: name of the volume group
    :returns: whether the volume group was found
    :rtype: bool
    """
    cmd = f"vgdisplay {vg_name}"
    try:
        process.run(cmd, sudo=True)
        LOGGER.debug("Provided volume group exists: %s", vg_name)
        return True
    except process.CmdError as exception:
        LOGGER.error(exception)
        return False


def vg_list(vg_name=None):
    """
    List all info about available volume groups.

    :param vg_name: name of the volume group to list or or None to list all
    :type vg_name: str or None
    :returns: list of available volume groups
    :rtype: {str, {str, str}}
    """
    cmd = "vgs --all"
    cmd += f" {vg_name}" if vg_name is not None else ""
    vgroups = {}
    result = process.run(cmd, sudo=True)
    lines = result.stdout_text.strip().splitlines()
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
            if "VG" in column:
                vg_name = details[index]
            else:
                details_dict[column] = details[index]
            index += 1
        vgroups[vg_name] = details_dict
    return vgroups


def vg_create(vg_name, pv_list, force=False):
    """
    Create a volume group from a list of physical volumes.

    :param str vg_name: name of the volume group
    :param pv_list: list of physical volumes to use
    :type pv_list: str or [str]
    :param bool force: create volume group with a force flag
    :raises: :py:class:`LVException` if volume group already exists
    """
    if vg_check(vg_name):
        raise LVException(f"Volume group '{vg_name}' already exist")
    cmd = "vgcreate"
    if isinstance(pv_list, list):
        pv_list = " ".join(pv_list)
    else:
        pv_list = str(pv_list)
    cmd += f" {vg_name} {pv_list}"
    if force:
        cmd += f"{cmd} -f -y"
    process.run(cmd, sudo=True)


def vg_remove(vg_name):
    """
    Remove a volume group.

    :param str vg_name: name of the volume group
    :raises: :py:class:`LVException` if volume group cannot be found
    """
    if not vg_check(vg_name):
        raise LVException(f"Volume group '{vg_name}' could not be found")
    cmd = f"vgremove -f {vg_name}"
    process.run(cmd, sudo=True)


def lv_check(vg_name, lv_name):
    """
    Check whether provided logical volume exists.

    :param str vg_name: name of the volume group
    :param str lv_name: name of the logical volume
    :return: whether the logical volume was found
    :rtype: bool
    """
    cmd = f"lvdisplay {vg_name}"
    result = process.run(cmd, ignore_status=True, sudo=True)

    lvpattern = fr"LV Name\s+{lv_name}\s+"
    match = re.search(lvpattern, result.stdout_text.rstrip())
    if match:
        LOGGER.debug("Provided Logical volume %s exists in %s",
                     lv_name, vg_name)
        return True
    else:
        return False


def lv_list(vg_name=None):
    """
    List all info about available logical volumes.

    :param str vg_name: name of the volume group or None to list all
    :returns: list of available logical volumes
    :rtype: {str, {str, str}}
    """
    cmd = "lvs --all"
    cmd += f" {vg_name}" if vg_name is not None else ""
    volumes = {}
    result = process.run(cmd, sudo=True)

    lines = result.stdout_text.strip().splitlines()
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


def lv_create(vg_name, lv_name, lv_size, force_flag=True,
              pool_name=None, pool_size="1G"):
    """
    Create a (possibly thin) logical volume in a volume group.
    The volume group must already exist.

    A thin pool will be created if pool parameters are provided
    and the thin pool doesn't already exist.

    The volume group must already exist.

    :param str vg_name: name of the volume group
    :param str lv_name: name of the logical volume
    :param str lv_size: size for the logical volume to be created
    :param bool force_flag: whether to abort if volume already exists
                            or remove and recreate it
    :param str pool_name: name of thin pool or None for a regular volume
    :param str pool_size: size of thin pool if it will be created
    :raises: :py:class:`LVException` if preconditions or execution fails
    """
    if not vg_check(vg_name):
        raise LVException("Volume group could not be found")
    if lv_check(vg_name, lv_name) and not force_flag:
        raise LVException("Logical volume already exists")
    elif lv_check(vg_name, lv_name) and force_flag:
        lv_remove(vg_name, lv_name)

    lv_cmd = f"lvcreate --name {lv_name}"
    if pool_name is not None:
        if not lv_check(vg_name, pool_name):
            tp_cmd = (f"lvcreate --thinpool {pool_name} "
                      f"--size {pool_size} {vg_name} -y")
            try:
                process.run(tp_cmd, sudo=True)
            except process.CmdError as detail:
                LOGGER.debug(detail)
                raise LVException("Create thin volume pool failed.")
            LOGGER.debug("Created thin volume pool: %s", pool_name)
        lv_cmd += f" --virtualsize {lv_size}"
        lv_cmd += f" --thin {vg_name}/{pool_name} -y"
    else:
        lv_cmd += f" --size {lv_size}"
        lv_cmd += f" {vg_name} -y"
    try:
        process.run(lv_cmd, sudo=True)
    except process.CmdError as detail:
        LOGGER.error(detail)
        raise LVException("Create thin volume failed.")
    LOGGER.debug("Created thin volume:%s", lv_name)


def lv_remove(vg_name, lv_name):
    """
    Remove a logical volume.

    :param str vg_name: name of the volume group
    :param str lv_name: name of the logical volume
    :raises: :py:class:`LVException` if volume group or logical
             volume cannot be found
    """
    if not vg_check(vg_name):
        raise LVException("Volume group could not be found")
    if not lv_check(vg_name, lv_name):
        raise LVException("Logical volume could not be found")

    cmd = f"lvremove -f /dev/{vg_name}/{lv_name}"
    process.run(cmd, sudo=True)


def lv_take_snapshot(vg_name, lv_name,
                     lv_snapshot_name, lv_snapshot_size=None,
                     pool_name=None):
    """
    Take a (possibly thin) snapshot of a regular (or thin) logical volume.

    :param str vg_name: name of the volume group
    :param str lv_name: name of the logical volume
    :param str lv_snapshot_name: name of the snapshot be to created
    :param str lv_snapshot_size: size of the snapshot or None for thin
                                 snapshot of an already thin volume
    :param pool_name: name of thin pool or None for regular snapshot
                      or snapshot in the same thin pool like the volume
    :raises: :py:class:`process.CmdError` on failure to create snapshot
    :raises: :py:class:`LVException` if preconditions fail
    """
    if not vg_check(vg_name):
        raise LVException("Volume group could not be found")
    if pool_name is not None and not lv_check(vg_name, pool_name):
        raise LVException("Snapshot's thin pool could not be found")
    if lv_check(vg_name, lv_snapshot_name):
        raise LVException("Snapshot already exists")
    if not lv_check(vg_name, lv_name):
        raise LVException("Snapshot's origin could not be found")

    # thin snapshot extensions (from thin or external volume)
    cmd = (f"lvcreate --snapshot --name {lv_snapshot_name} "
           f"/dev/{vg_name}/{lv_name} --ignoreactivationskip")
    if lv_snapshot_size is not None:
        cmd += f" --size {lv_snapshot_size}"
    if pool_name is not None:
        cmd += f" --thinpool {vg_name}/{pool_name}"

    try:
        process.run(cmd, sudo=True)
    except process.CmdError as ex:
        lv = (f'Logical volume "{lv_snapshot_name}" already exists '
              f'in volume group "{vg_name}"')
        if lv in ex.result.stderr_text:
            active = lv_snapshot_name + " [active]" in process.run("lvdisplay", sudo=True).stdout_text
            if active:
                # the above conditions detect if merge of snapshot was postponed
                log_msg = "Logical volume %s is still active! Attempting to deactivate..."
                LOGGER.debug(log_msg, lv_name)
                lv_reactivate(vg_name, lv_name)
                process.run(cmd, sudo=True)
        else:
            raise ex


def lv_revert(vg_name, lv_name, lv_snapshot_name):
    """
    Revert the origin logical volume to a snapshot.

    :param str vg_name: name of the volume group
    :param str lv_name: name of the logical volume
    :param str lv_snapshot_name: name of the snapshot to be reverted
    :raises: :py:class:`process.CmdError` on failure to revert snapshot
    :raises: :py:class:`LVException` if preconditions or execution fails
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

        cmd = (f"lvconvert --merge --interval 1 "
               f"/dev/{vg_name}/{lv_snapshot_name}")
        result = process.run(cmd, sudo=True)
        if ((f"Merging of snapshot {lv_snapshot_name} will start "
             f"next activation.") in result.stdout_text):
            raise LVException(f"The Logical volume {lv_name} is still active")

    except process.CmdError as ex:
        # detect if merge of snapshot was postponed
        # and attempt to reactivate the volume.
        active_lv_pattern = re.escape(f"{lv_snapshot_name} [active]")
        lvdisplay_output = process.run("lvdisplay", sudo=True).stdout_text
        if ('Snapshot could not be found' in ex.result.stderr_text and
                re.search(active_lv_pattern, lvdisplay_output) or
                f"The Logical volume {lv_name} is still active" in ex.result.stderr_text):
            log_msg = "Logical volume %s is still active! Attempting to deactivate..."
            LOGGER.debug(log_msg, lv_name)
            lv_reactivate(vg_name, lv_name)
            LOGGER.error("Continuing after reactivation")
        elif 'Snapshot could not be found' in ex.result.stderr_text:
            LOGGER.error("Could not revert to snapshot:")
            LOGGER.error(ex.result)
        else:
            raise ex


def lv_revert_with_snapshot(vg_name, lv_name,
                            lv_snapshot_name, lv_snapshot_size):
    """
    Perform logical volume merge with snapshot and take a new snapshot.

    :param str vg_name: name of the volume group
    :param str lv_name: name of the logical volume
    :param str lv_snapshot_name: name of the snapshot to be reverted
    :param str lv_snapshot_size: size of the snapshot
    """
    lv_revert(vg_name, lv_name, lv_snapshot_name)
    lv_take_snapshot(vg_name, lv_name, lv_snapshot_name, lv_snapshot_size)


def lv_reactivate(vg_name, lv_name, timeout=10):
    """
    In case of unclean shutdowns some of the lvs is still active and merging
    is postponed. Use this function to attempt to deactivate and reactivate
    all of them to cause the merge to happen.

    :param str vg_name: name of the volume group
    :param str lv_name: name of the logical volume
    :param int timeout: timeout between operations
    :raises: :py:class:`LVException` if the logical volume is still active
    """
    try:
        process.run(f"lvchange -an /dev/{vg_name}/{lv_name}", sudo=True)
        time.sleep(timeout)
        process.run(f"lvchange -ay /dev/{vg_name}/{lv_name}", sudo=True)
        time.sleep(timeout)
    except process.CmdError:
        log_msg = "Failed to reactivate %s - please, nuke the process that uses it first."
        LOGGER.error(log_msg, lv_name)
        raise LVException(f"The Logical volume {lv_name} is still active")


def lv_mount(vg_name, lv_name, mount_loc, create_filesystem=""):
    """
    Mount a logical volume to a mount location.

    :param str vg_name: name of the volume group
    :param str lv_name: name of the logical volume
    :param str mount_loc: location to mount the logical volume to
    :param str create_filesystem: can be one of ext2, ext3, ext4, vfat or empty
                                  if the filesystem was already created and the
                                  mkfs process is skipped
    :raises: :py:class:`LVException` if the logical volume could not be mounted
    """
    try:
        if create_filesystem:
            process.run(f"mkfs.{create_filesystem} /dev/{vg_name}/{lv_name}",
                        sudo=True)
        process.run(f"mount /dev/{vg_name}/{lv_name} {mount_loc}", sudo=True)
    except process.CmdError as ex:
        raise LVException(f"Fail to mount logical volume: {ex}")


def vg_reactivate(vg_name, timeout=10, export=False):
    """
    In case of unclean shutdowns some of the vgs is still active and merging
    is postponed. Use this function to attempt to deactivate and reactivate
    all of them to cause the merge to happen.

    :param str vg_name: name of the volume group
    :param int timeout: timeout between operations
    :raises: :py:class:`LVException` if the logical volume is still active
    """
    try:
        process.run(f"vgchange -an {vg_name}", sudo=True)
        time.sleep(timeout)

        if export:
            process.run(f"vgexport {vg_name}", sudo=True)
            time.sleep(timeout)
            process.run(f"vgimport {vg_name}", sudo=True)
            time.sleep(timeout)

        process.run(f"vgchange -ay {vg_name}", sudo=True)
        time.sleep(timeout)
    except process.CmdError:
        log_msg = "Failed to reactivate %s - please, nuke the process that uses it first."
        LOGGER.error(log_msg, vg_name)
        raise LVException(f"The Volume group {vg_name} is still active")


def lv_umount(vg_name, lv_name):
    """
    Unmount a Logical volume from a mount location.

    :param str vg_name: name of the volume group
    :param str lv_name: name of the logical volume
    :raises: :py:class:`LVException` if the logical volume could not be unmounted
    """
    try:
        process.run(f"umount /dev/{vg_name}/{lv_name}", sudo=True)
    except process.CmdError as ex:
        raise LVException(f"Fail to unmount logical volume: {ex}")
