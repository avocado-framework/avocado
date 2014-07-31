"""
Utilities to create logical volumes or take snapshots of existing ones.

:author: Plamen Dimitrov
:copyright: Intra2net AG 2012
:license: GPL v2

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

Sample ramdisk params:

::

    ramdisk_vg_size = "40000"
    ramdisk_basedir = "/tmp"
    ramdisk_sparse_filename = "virtual_hdd"

Sample general params:

::

    vg_name='autotest_vg',
    lv_name='autotest_lv',
    lv_size='1G',
    lv_snapshot_name='autotest_sn',
    lv_snapshot_size='1G'

The ramdisk volume group size is in MB.
"""

import logging
import re
import os
import shutil
import time

from autotest.client import utils
from autotest.client.shared import error


@error.context_aware
def vg_ramdisk(vg_name, ramdisk_vg_size,
               ramdisk_basedir, ramdisk_sparse_filename):
    """
    Create vg on top of ram memory to speed up lv performance.
    """
    error.context("Creating virtual group on top of ram memory",
                  logging.info)
    vg_size = ramdisk_vg_size
    vg_ramdisk_dir = os.path.join(ramdisk_basedir, vg_name)
    ramdisk_filename = os.path.join(vg_ramdisk_dir,
                                    ramdisk_sparse_filename)

    vg_ramdisk_cleanup(ramdisk_filename,
                       vg_ramdisk_dir, vg_name, "")
    result = ""
    if not os.path.exists(vg_ramdisk_dir):
        os.mkdir(vg_ramdisk_dir)
    try:
        logging.info("Mounting tmpfs")
        result = utils.run("mount -t tmpfs tmpfs " + vg_ramdisk_dir)

        logging.info("Converting and copying /dev/zero")
        cmd = ("dd if=/dev/zero of=" + ramdisk_filename +
               " bs=1M count=1 seek=" + vg_size)
        result = utils.run(cmd, verbose=True)

        logging.info("Finding free loop device")
        result = utils.run("losetup --find", verbose=True)
    except error.CmdError, ex:
        logging.error(ex)
        vg_ramdisk_cleanup(ramdisk_filename,
                           vg_ramdisk_dir, vg_name, "")
        raise ex

    loop_device = result.stdout.rstrip()

    try:
        logging.info("Creating loop device")
        result = utils.run("losetup " + loop_device + " " + ramdisk_filename)
        logging.info("Creating physical volume %s", loop_device)
        result = utils.run("pvcreate " + loop_device)
        logging.info("Creating volume group %s", vg_name)
        result = utils.run("vgcreate " + vg_name + " " + loop_device)
    except error.CmdError, ex:
        logging.error(ex)
        vg_ramdisk_cleanup(ramdisk_filename, vg_ramdisk_dir, vg_name,
                           loop_device)
        raise ex

    logging.info(result.stdout.rstrip())


def vg_ramdisk_cleanup(ramdisk_filename, vg_ramdisk_dir,
                       vg_name, loop_device):
    """
    Inline cleanup function in case of test error.
    """
    result = utils.run("vgremove " + vg_name, ignore_status=True)
    if result.exit_status == 0:
        logging.info(result.stdout.rstrip())
    else:
        logging.debug("%s -> %s", result.command, result.stderr)

    result = utils.run("pvremove " + loop_device, ignore_status=True)
    if result.exit_status == 0:
        logging.info(result.stdout.rstrip())
    else:
        logging.debug("%s -> %s", result.command, result.stderr)

    for _ in range(10):
        time.sleep(0.1)
        result = utils.run("losetup -d " + loop_device, ignore_status=True)
        if "resource busy" not in result.stderr:
            if result.exit_status != 0:
                logging.debug("%s -> %s", result.command, result.stderr)
            else:
                logging.info("Loop device %s deleted", loop_device)
            break

    if os.path.exists(ramdisk_filename):
        os.unlink(ramdisk_filename)
        logging.info("Ramdisk filename %s deleted", ramdisk_filename)

    utils.run("umount " + vg_ramdisk_dir, ignore_status=True)
    if result.exit_status == 0:
        if loop_device != "":
            logging.info("Loop device %s unmounted", loop_device)
    else:
        logging.debug("%s -> %s", result.command, result.stderr)

    if os.path.exists(vg_ramdisk_dir):
        try:
            shutil.rmtree(vg_ramdisk_dir)
            logging.info("Ramdisk directory %s deleted", vg_ramdisk_dir)
        except OSError:
            pass


def vg_check(vg_name):
    """
    Check whether provided volume group exists.
    """
    cmd = "vgdisplay " + vg_name
    try:
        utils.run(cmd)
        logging.debug("Provided volume group exists: " + vg_name)
        return True
    except error.CmdError:
        return False


def vg_list():
    """
    List available volume groups.
    """
    cmd = "vgs --all"
    vgroups = {}
    result = utils.run(cmd)

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


@error.context_aware
def vg_create(vg_name, pv_list):
    """
    Create a volume group by using the block special devices
    """
    error.context(
        "Creating volume group '%s' by using '%s'" %
        (vg_name, pv_list), logging.info)

    if vg_check(vg_name):
        raise error.TestError("Volume group '%s' already exist" % vg_name)
    cmd = "vgcreate %s %s" % (vg_name, pv_list)
    result = utils.run(cmd)
    logging.info(result.stdout.rstrip())


@error.context_aware
def vg_remove(vg_name):
    """
    Remove a volume group.
    """
    error.context("Removing volume '%s'" % vg_name, logging.info)

    if not vg_check(vg_name):
        raise error.TestError("Volume group '%s' could not be found" % vg_name)
    cmd = "vgremove -f %s" % vg_name
    result = utils.run(cmd)
    logging.info(result.stdout.rstrip())


def lv_check(vg_name, lv_name):
    """
    Check whether provided logical volume exists.
    """
    cmd = "lvdisplay"
    result = utils.run(cmd, ignore_status=True)

    # unstable approach but currently works
    lvpattern = r"LV Path\s+/dev/" + vg_name + r"/" + lv_name + "\s+"
    match = re.search(lvpattern, result.stdout.rstrip())
    if match:
        logging.debug("Provided logical volume exists: /dev/" +
                      vg_name + "/" + lv_name)
        return True
    else:
        return False


@error.context_aware
def lv_remove(vg_name, lv_name):
    """
    Remove a logical volume.
    """
    error.context("Removing volume /dev/%s/%s" %
                  (vg_name, lv_name), logging.info)

    if not vg_check(vg_name):
        raise error.TestError("Volume group could not be found")
    if not lv_check(vg_name, lv_name):
        raise error.TestError("Logical volume could not be found")

    cmd = "lvremove -f " + vg_name + "/" + lv_name
    result = utils.run(cmd)
    logging.info(result.stdout.rstrip())


@error.context_aware
def lv_create(vg_name, lv_name, lv_size, force_flag=True):
    """
    Create a logical volume in a volume group.

    The volume group must already exist.
    """
    error.context("Creating original lv to take a snapshot from",
                  logging.info)

    if not vg_check(vg_name):
        raise error.TestError("Volume group could not be found")
    if lv_check(vg_name, lv_name) and not force_flag:
        raise error.TestError("Logical volume already exists")
    elif lv_check(vg_name, lv_name) and force_flag:
        lv_remove(vg_name, lv_name)

    cmd = ("lvcreate --size " + lv_size + " --name " + lv_name + " " + vg_name)
    result = utils.run(cmd)
    logging.info(result.stdout.rstrip())


@error.context_aware
def lv_take_snapshot(vg_name, lv_name,
                     lv_snapshot_name, lv_snapshot_size):
    """
    Take a snapshot of the original logical volume.
    """
    error.context("Taking snapshot from original logical volume",
                  logging.info)

    if not vg_check(vg_name):
        raise error.TestError("Volume group could not be found")
    if lv_check(vg_name, lv_snapshot_name):
        raise error.TestError("Snapshot already exists")
    if not lv_check(vg_name, lv_name):
        raise error.TestError("Snapshot's origin could not be found")

    cmd = ("lvcreate --size " + lv_snapshot_size + " --snapshot " +
           " --name " + lv_snapshot_name + " /dev/" + vg_name + "/" + lv_name)
    try:
        result = utils.run(cmd)
    except error.CmdError, ex:
        if ('Logical volume "%s" already exists in volume group "%s"' %
            (lv_snapshot_name, vg_name) in ex.result_obj.stderr and
            re.search(re.escape(lv_snapshot_name + " [active]"),
                      utils.run("lvdisplay").stdout)):
            # the above conditions detect if merge of snapshot was postponed
            logging.warning(("Logical volume %s is still active! " +
                             "Attempting to deactivate..."), lv_name)
            lv_reactivate(vg_name, lv_name)
            result = utils.run(cmd)
        else:
            raise ex
    logging.info(result.stdout.rstrip())


@error.context_aware
def lv_revert(vg_name, lv_name, lv_snapshot_name):
    """
    Revert the origin to a snapshot.
    """
    error.context("Reverting original logical volume to snapshot",
                  logging.info)
    try:
        if not vg_check(vg_name):
            raise error.TestError("Volume group could not be found")
        if not lv_check(vg_name, lv_snapshot_name):
            raise error.TestError("Snapshot could not be found")
        if (not lv_check(vg_name, lv_snapshot_name)
                and not lv_check(vg_name, lv_name)):
            raise error.TestError("Snapshot and its origin could not be found")
        if (lv_check(vg_name, lv_snapshot_name)
                and not lv_check(vg_name, lv_name)):
            raise error.TestError("Snapshot origin could not be found")

        cmd = ("lvconvert --merge /dev/%s/%s" % (vg_name, lv_snapshot_name))
        result = utils.run(cmd)
        if ("Merging of snapshot %s will start next activation." %
                lv_snapshot_name) in result.stdout:
            raise error.TestError("The logical volume %s is still active" %
                                  lv_name)
        result = result.stdout.rstrip()

    except error.TestError, ex:
        # detect if merge of snapshot was postponed
        # and attempt to reactivate the volume.
        if (('Snapshot could not be found' in ex and
             re.search(re.escape(lv_snapshot_name + " [active]"),
                       utils.run("lvdisplay").stdout))
                or ("The logical volume %s is still active" % lv_name) in ex):
            logging.warning(("Logical volume %s is still active! " +
                             "Attempting to deactivate..."), lv_name)
            lv_reactivate(vg_name, lv_name)
            result = "Continuing after reactivation"
        elif 'Snapshot could not be found' in ex:
            logging.error(ex)
            result = "Could not revert to snapshot"
        else:
            raise ex
    logging.info(result)


@error.context_aware
def lv_revert_with_snapshot(vg_name, lv_name,
                            lv_snapshot_name, lv_snapshot_size):
    """
    Perform logical volume merge with snapshot and take a new snapshot.

    """
    error.context("Reverting to snapshot and taking a new one",
                  logging.info)

    lv_revert(vg_name, lv_name, lv_snapshot_name)
    lv_take_snapshot(vg_name, lv_name, lv_snapshot_name, lv_snapshot_size)


@error.context_aware
def lv_reactivate(vg_name, lv_name, timeout=10):
    """
    In case of unclean shutdowns some of the lvs is still active and merging
    is postponed. Use this function to attempt to deactivate and reactivate
    all of them to cause the merge to happen.
    """
    try:
        utils.run("lvchange -an /dev/%s/%s" % (vg_name, lv_name))
        time.sleep(timeout)
        utils.run("lvchange -ay /dev/%s/%s" % (vg_name, lv_name))
        time.sleep(timeout)
    except error.CmdError:
        logging.error(("Failed to reactivate %s - please, " +
                       "nuke the process that uses it first."), lv_name)
        raise error.TestError("The logical volume %s is still active" % lv_name)
