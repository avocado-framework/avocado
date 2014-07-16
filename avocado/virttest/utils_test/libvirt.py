"""
High-level libvirt test utility functions.

This module is meant to reduce code size by performing common test procedures.
Generally, code here should look like test code.

More specifically:
    - Functions in this module should raise exceptions if things go wrong
    - Functions in this module typically use functions and classes from
      lower-level modules (e.g. utils_misc, qemu_vm, aexpect).
    - Functions in this module should not be used by lower-level modules.
    - Functions in this module should be used in the right context.
      For example, a function should not be used where it may display
      misleading or inaccurate info or debug messages.

:copyright: 2014 Red Hat Inc.
"""

import re
import os
import logging
import shutil
import threading
import time
from virttest import virsh
from virttest import xml_utils
from virttest import iscsi
from virttest import nfs
from virttest import data_dir
from virttest import aexpect
from virttest import utils_misc
from virttest import utils_selinux
from virttest import libvirt_storage
from virttest import utils_net
from virttest import gluster
from autotest.client import utils
from autotest.client.shared import error
from virttest.libvirt_xml import vm_xml
from virttest.libvirt_xml import xcepts
from virttest.libvirt_xml.devices import disk
from __init__ import ping
try:
    from autotest.client import lv_utils
except ImportError:
    from virttest.staging import lv_utils


def cpus_parser(cpulist):
    """
    Parse a list of cpu list, its syntax is a comma separated list,
    with '-' for ranges and '^' denotes exclusive.
    :param cpulist: a list of physical CPU numbers
    """
    hyphens = []
    carets = []
    commas = []
    others = []

    if cpulist is None:
        return None

    else:
        if "," in cpulist:
            cpulist_list = re.split(",", cpulist)
            for cpulist in cpulist_list:
                if "-" in cpulist:
                    tmp = re.split("-", cpulist)
                    hyphens = hyphens + range(int(tmp[0]), int(tmp[-1]) + 1)
                elif "^" in cpulist:
                    tmp = re.split("\^", cpulist)[-1]
                    carets.append(int(tmp))
                else:
                    try:
                        commas.append(int(cpulist))
                    except ValueError:
                        logging.error("The cpulist has to be an "
                                      "integer. (%s)", cpulist)
        elif "-" in cpulist:
            tmp = re.split("-", cpulist)
            hyphens = range(int(tmp[0]), int(tmp[-1]) + 1)
        elif "^" in cpulist:
            tmp = re.split("^", cpulist)[-1]
            carets.append(int(tmp))
        else:
            try:
                others.append(int(cpulist))
                return others
            except ValueError:
                logging.error("The cpulist has to be an "
                              "integer. (%s)", cpulist)

        cpus_set = set(hyphens).union(set(commas)).difference(set(carets))

        return sorted(list(cpus_set))


def cpus_string_to_affinity_list(cpus_string, num_cpus):
    """
    Parse the cpus_string string to a affinity list.

    e.g
    host_cpu_count = 4
    0       -->     [y,-,-,-]
    0,1     -->     [y,y,-,-]
    0-2     -->     [y,y,y,-]
    0-2,^2  -->     [y,y,-,-]
    r       -->     [y,y,y,y]
    """
    # Check the input string.
    single_pattern = r"\d+"
    between_pattern = r"\d+-\d+"
    exclude_pattern = r"\^\d+"
    sub_pattern = r"(%s)|(%s)|(%s)" % (exclude_pattern,
                                       single_pattern, between_pattern)
    pattern = r"^((%s),)*(%s)$" % (sub_pattern, sub_pattern)
    if not re.match(pattern, cpus_string):
        logging.debug("Cpus_string=%s is not a supported format for cpu_list."
                      % cpus_string)
    # Init a list for result.
    affinity = []
    for i in range(int(num_cpus)):
        affinity.append('-')
    # Letter 'r' means all cpus.
    if cpus_string == "r":
        for i in range(len(affinity)):
            affinity[i] = "y"
        return affinity
    # Split the string with ','.
    sub_cpus = cpus_string.split(",")
    # Parse each sub_cpus.
    for cpus in sub_cpus:
        if "-" in cpus:
            minmum = cpus.split("-")[0]
            maxmum = cpus.split("-")[-1]
            for i in range(int(minmum), int(maxmum) + 1):
                affinity[i] = "y"
        elif "^" in cpus:
            affinity[int(cpus.strip("^"))] = "-"
        else:
            affinity[int(cpus)] = "y"
    return affinity


def cpu_allowed_list_by_task(pid, tid):
    """
    Get the Cpus_allowed_list in status of task.
    """
    cmd = "cat /proc/%s/task/%s/status|grep Cpus_allowed_list:| awk '{print $2}'" % (pid, tid)
    result = utils.run(cmd, ignore_status=True)
    if result.exit_status:
        return None
    return result.stdout.strip()


def clean_up_snapshots(vm_name, snapshot_list=[]):
    """
    Do recovery after snapshot

    :param vm_name: Name of domain
    :param snapshot_list: The list of snapshot name you want to remove
    """
    if not snapshot_list:
        # Get all snapshot names from virsh snapshot-list
        snapshot_list = virsh.snapshot_list(vm_name)

        # Get snapshot disk path
        for snap_name in snapshot_list:
            # Delete useless disk snapshot file if exists
            snap_xml = virsh.snapshot_dumpxml(vm_name,
                                              snap_name).stdout.strip()
            xtf_xml = xml_utils.XMLTreeFile(snap_xml)
            disks_path = xtf_xml.findall('disks/disk/source')
            for disk in disks_path:
                os.system('rm -f %s' % disk.get('file'))
            # Delete snapshots of vm
            virsh.snapshot_delete(vm_name, snap_name)
    else:
        # Get snapshot disk path from domain xml because
        # there is no snapshot info with the name
        dom_xml = vm_xml.VMXML.new_from_dumpxml(vm_name).xmltreefile
        disk_path = dom_xml.find('devices/disk/source').get('file')
        for name in snapshot_list:
            snap_disk_path = disk_path.split(".")[0] + "." + name
            os.system('rm -f %s' % snap_disk_path)


def get_all_cells():
    """
    Use virsh freecell --all to get all cells on host

    ::

        # virsh freecell --all
            0:     124200 KiB
            1:    1059868 KiB
        --------------------
        Total:    1184068 KiB

    That would return a dict like:

    ::

        cell_dict = {"0":"124200 KiB", "1":"1059868 KiB", "Total":"1184068 KiB"}

    :return: cell_dict
    """
    fc_result = virsh.freecell(options="--all", ignore_status=True)
    if fc_result.exit_status:
        if fc_result.stderr.count("NUMA not supported"):
            raise error.TestNAError(fc_result.stderr.strip())
        else:
            raise error.TestFail(fc_result.stderr.strip())
    output = fc_result.stdout.strip()
    cell_list = output.splitlines()
    # remove "------------" line
    del cell_list[-2]
    cell_dict = {}
    for cell_line in cell_list:
        cell_info = cell_line.split(":")
        cell_num = cell_info[0].strip()
        cell_mem = cell_info[-1].strip()
        cell_dict[cell_num] = cell_mem
    return cell_dict


def check_blockjob(vm_name, target, check_point="none", value="0"):
    """
    Run blookjob command to check block job progress, bandwidth, ect.

    :param vm_name: Domain name
    :param target: Domian disk target dev
    :param check_point: Job progrss, bandwidth or none(no job)
    :param value: Value of progress, bandwidth or 0(no job)
    :return: Boolean value, true for pass, false for fail
    """
    if check_point not in ["progress", "bandwidth", "none"]:
        logging.error("Check point must be: progress, bandwidth or none")
        return False

    try:
        cmd_result = virsh.blockjob(vm_name, target, "--info", ignore_status=True)
        output = cmd_result.stdout.strip()
        err = cmd_result.stderr.strip()
        status = cmd_result.exit_status
    except:
        raise error.TestFail("Error occur when running blockjob command.")
    if status == 0:
        # libvirt print job progress to stderr
        if not len(err):
            logging.debug("No block job find")
            if check_point == "none":
                return True
        else:
            if check_point == "none":
                logging.error("Expect no job but find block job:\n%s", err)
            elif check_point == "progress":
                progress = value + " %"
                if re.search(progress, err):
                    return True
            elif check_point == "bandwidth":
                bandwidth = value + " MiB/s"
                if bandwidth == output.split(':')[1].strip():
                    logging.debug("Bandwidth is equal to %s", bandwidth)
                    return True
                else:
                    logging.error("Bandwidth is not equal to %s", bandwidth)
    else:
        logging.error("Run blockjob command fail")
    return False


def setup_or_cleanup_nfs(is_setup, mount_dir="", is_mount=False,
                         export_options="rw,no_root_squash",
                         mount_src="nfs-export"):
    """
    Set up or clean up nfs service on localhost.

    :param is_setup: Boolean value, true for setup, false for cleanup
    :param mount_dir: NFS mount point
    :param is_mount: Boolean value, true for mount, false for umount
    :param export_options: options for nfs dir
    :return: export nfs path or nothing
    """
    tmpdir = os.path.join(data_dir.get_root_dir(), 'tmp')
    if not os.path.isabs(mount_src):
        mount_src = os.path.join(tmpdir, mount_src)
    if not mount_dir:
        mount_dir = os.path.join(tmpdir, 'nfs-mount')

    nfs_params = {"nfs_mount_dir": mount_dir, "nfs_mount_options": "rw",
                  "nfs_mount_src": mount_src, "setup_local_nfs": "yes",
                  "export_options": "rw,no_root_squash"}
    _nfs = nfs.Nfs(nfs_params)
    # Set selinux to permissive that the file in nfs
    # can be used freely
    if utils_selinux.is_enforcing():
        sv_status = utils_selinux.get_status()
        utils_selinux.set_status("permissive")
    if is_setup:
        _nfs.setup()
        if not is_mount:
            _nfs.umount()
        return mount_src
    else:
        _nfs.unexportfs_in_clean = True
        _nfs.cleanup()
        return ""


def setup_or_cleanup_iscsi(is_setup, is_login=True,
                           emulated_image="emulated_iscsi", image_size="1G"):
    """
    Set up(and login iscsi target) or clean up iscsi service on localhost.

    :param is_setup: Boolean value, true for setup, false for cleanup
    :param is_login: Boolean value, true for login, false for not login
    :param emulated_image: name of iscsi device
    :param image_size: emulated image's size
    :return: iscsi device name or iscsi target
    """
    try:
        utils_misc.find_command("tgtadm")
        utils_misc.find_command("iscsiadm")
    except ValueError:
        raise error.TestNAError("Missing command 'tgtadm' and/or 'iscsiadm'.")

    tmpdir = os.path.join(data_dir.get_root_dir(), 'tmp')
    emulated_path = os.path.join(tmpdir, emulated_image)
    emulated_target = "iqn.2001-01.com.virttest:%s.target" % emulated_image
    iscsi_params = {"emulated_image": emulated_path, "target": emulated_target,
                    "image_size": image_size, "iscsi_thread_id": "virt"}
    _iscsi = iscsi.Iscsi(iscsi_params)
    if is_setup:
        sv_status = None
        if utils_selinux.is_enforcing():
            sv_status = utils_selinux.get_status()
            utils_selinux.set_status("permissive")
        _iscsi.export_target()
        if sv_status is not None:
            utils_selinux.set_status(sv_status)
        if is_login:
            _iscsi.login()
            # The device doesn't necessarily appear instantaneously, so give
            # about 5 seconds for it to appear before giving up
            iscsi_device = utils_misc.wait_for(_iscsi.get_device_name, 5, 0, 1,
                                               "Searching iscsi device name.")
            if iscsi_device:
                logging.debug("iscsi device: %s", iscsi_device)
                return iscsi_device
            if not iscsi_device:
                logging.error("Not find iscsi device.")
            # Cleanup and return "" - caller needs to handle that
            # _iscsi.export_target() will have set the emulated_id and
            # export_flag already on success...
            _iscsi.cleanup()
            utils.run("rm -f %s" % emulated_path)
        else:
            return emulated_target
    else:
        _iscsi.export_flag = True
        _iscsi.emulated_id = _iscsi.get_target_id()
        _iscsi.cleanup()
        utils.run("rm -f %s" % emulated_path)
    return ""


def get_host_ipv4_addr():
    """
    Get host ipv4 addr
    """
    if_up = utils_net.get_net_if(state="UP")
    for i in if_up:
        ipv4_value = utils_net.get_net_if_addrs(i)["ipv4"]
        logging.debug("ipv4_value is %s", ipv4_value)
        if ipv4_value != []:
            ip_addr = ipv4_value[0]
            break
    if ip_addr is not None:
        logging.info("ipv4 address is %s", ip_addr)
    else:
        raise error.TestFail("Fail to get ip address")
    return ip_addr


def setup_or_cleanup_gluster(is_setup, vol_name, brick_path="", pool_name=""):
    """
    Set up or clean up glusterfs environment on localhost
    :param is_setup: Boolean value, true for setup, false for cleanup
    :param vol_name: gluster created volume name
    :param brick_path: Dir for create glusterfs
    :return: ip_addr or nothing
    """
    if not brick_path:
        tmpdir = os.path.join(data_dir.get_root_dir(), 'tmp')
        brick_path = os.path.join(tmpdir, pool_name)
    if is_setup:
        ip_addr = get_host_ipv4_addr()
        gluster.glusterd_start()
        logging.debug("finish start gluster")
        gluster.gluster_vol_create(vol_name, ip_addr, brick_path)
        logging.debug("finish vol create in gluster")
        return ip_addr
    else:
        gluster.gluster_vol_stop(vol_name, True)
        gluster.gluster_vol_delete(vol_name)
        gluster.gluster_brick_delete(brick_path)
        return ""


def define_pool(pool_name, pool_type, pool_target, cleanup_flag):
    """
    To define a given type pool(Support types: 'dir', 'netfs', logical',
    iscsi', 'disk' and 'fs').

    :param pool_name: Name of the pool
    :param pool_type: Type of the pool
    :param pool_target: Target for underlying storage
    """
    extra = ""
    vg_name = pool_name
    cleanup_nfs = False
    cleanup_iscsi = False
    cleanup_logical = False
    if not os.path.exists(pool_target):
        os.mkdir(pool_target)
    if pool_type == "dir":
        pass
    elif pool_type == "netfs":
        # Set up NFS server without mount
        nfs_path = setup_or_cleanup_nfs(True, pool_target, False)
        cleanup_nfs = True
        extra = "--source-host %s --source-path %s" % ('localhost',
                                                       nfs_path)
    elif pool_type == "logical":
        # Create vg by using iscsi device
        lv_utils.vg_create(vg_name, setup_or_cleanup_iscsi(True))
        cleanup_iscsi = True
        cleanup_logical = True
        extra = "--source-name %s" % vg_name
    elif pool_type == "iscsi":
        # Set up iscsi target without login
        iscsi_target = setup_or_cleanup_iscsi(True, False)
        cleanup_iscsi = True
        extra = "--source-host %s  --source-dev %s" % ('localhost',
                                                       iscsi_target)
    elif pool_type == "disk":
        # Set up iscsi target and login
        device_name = setup_or_cleanup_iscsi(True)
        cleanup_iscsi = True
        # Create a partition to make sure disk pool can start
        cmd = "parted -s %s mklabel msdos" % device_name
        utils.run(cmd)
        cmd = "parted -s %s mkpart primary ext4 0 100" % device_name
        utils.run(cmd)
        extra = "--source-dev %s" % device_name
    elif pool_type == "fs":
        # Set up iscsi target and login
        device_name = setup_or_cleanup_iscsi(True)
        cleanup_iscsi = True
        # Format disk to make sure fs pool can start
        cmd = "mkfs.ext4 -F %s" % device_name
        utils.run(cmd)
        extra = "--source-dev %s" % device_name
    elif pool_type in ["scsi", "mpath", "rbd", "sheepdog"]:
        raise error.TestNAError(
            "Pool type '%s' has not yet been supported in the test." %
            pool_type)
    else:
        raise error.TestFail("Invalid pool type: '%s'." % pool_type)
    # Mark the clean up flags
    cleanup_flag[0] = cleanup_nfs
    cleanup_flag[1] = cleanup_iscsi
    cleanup_flag[2] = cleanup_logical
    try:
        result = virsh.pool_define_as(pool_name, pool_type, pool_target, extra,
                                      ignore_status=True)
    except error.CmdError:
        logging.error("Define '%s' type pool fail.", pool_type)
    return result


def verify_virsh_console(session, user, passwd, timeout=10, debug=False):
    """
    Run commands in console session.
    """
    log = ""
    console_cmd = "cat /proc/cpuinfo"
    try:
        while True:
            match, text = session.read_until_last_line_matches(
                [r"[E|e]scape character is", r"login:",
                 r"[P|p]assword:", session.prompt],
                timeout, internal_timeout=1)

            if match == 0:
                if debug:
                    logging.debug("Got '^]', sending '\\n'")
                session.sendline()
            elif match == 1:
                if debug:
                    logging.debug("Got 'login:', sending '%s'", user)
                session.sendline(user)
            elif match == 2:
                if debug:
                    logging.debug("Got 'Password:', sending '%s'", passwd)
                session.sendline(passwd)
            elif match == 3:
                if debug:
                    logging.debug("Got Shell prompt -- logged in")
                break

        status, output = session.cmd_status_output(console_cmd)
        logging.info("output of command:\n%s", output)
        session.close()
    except (aexpect.ShellError,
            aexpect.ExpectError), detail:
        log = session.get_output()
        logging.error("Verify virsh console failed:\n%s\n%s", detail, log)
        session.close()
        return False

    if not re.search("processor", output):
        logging.error("Verify virsh console failed: Result does not match.")
        return False

    return True


def pci_label_from_address(address_dict, radix=10):
    """
    Generate a pci label from a dict of address.

    :param address_dict: A dict contains domain, bus, slot and function.
    :param radix: The radix of your data in address_dict.

    Example:

    ::

        address_dict = {'domain': '0x0000', 'bus': '0x08', 'slot': '0x10', 'function': '0x0'}
        radix = 16
        return = pci_0000_08_10_0
    """
    if not set(['domain', 'bus', 'slot', 'function']).issubset(
            address_dict.keys()):
        raise error.TestError("Param %s does not contain keys of "
                              "['domain', 'bus', 'slot', 'function']." %
                              str(address_dict))
    domain = int(address_dict['domain'], radix)
    bus = int(address_dict['bus'], radix)
    slot = int(address_dict['slot'], radix)
    function = int(address_dict['function'], radix)
    pci_label = ("pci_%04x_%02x_%02x_%01x" % (domain, bus, slot, function))
    return pci_label


def mk_part(disk, size="100M", session=None):
    """
    Create a partition for disk
    """
    mklabel_cmd = "parted -s %s mklabel msdos" % disk
    mkpart_cmd = "parted -s %s mkpart primary ext4 0 %s" % (disk, size)
    if session:
        session.cmd(mklabel_cmd)
        session.cmd(mkpart_cmd)
    else:
        utils.run(mklabel_cmd)
        utils.run(mkpart_cmd)


def mkfs(partition, fs_type, options="", session=None):
    """
    Make a file system on the partition
    """
    mkfs_cmd = "mkfs.%s -F %s %s" % (fs_type, partition, options)
    if session:
        session.cmd(mkfs_cmd)
    else:
        utils.run(mkfs_cmd)


def check_actived_pool(pool_name):
    """
    Check if pool_name exist in active pool list
    """
    sp = libvirt_storage.StoragePool()
    if not sp.pool_exists(pool_name):
        raise error.TestFail("Can't find pool %s" % pool_name)
    if not sp.is_pool_active(pool_name):
        raise error.TestFail("Pool %s is not active." % pool_name)
    logging.debug("Find active pool %s", pool_name)
    return True


class PoolVolumeTest(object):

    """Test class for storage pool or volume"""

    def __init__(self, test, params):
        self.tmpdir = test.tmpdir
        self.params = params

    def cleanup_pool(self, pool_name, pool_type, pool_target, emulated_image,
                     source_name=None):
        """
        Delete vols, destroy the created pool and restore the env
        """
        sp = libvirt_storage.StoragePool()
        try:
            if sp.pool_exists(pool_name):
                pv = libvirt_storage.PoolVolume(pool_name)
                if pool_type in ["dir", "netfs", "logical", "disk"]:
                    vols = pv.list_volumes()
                    for vol in vols:
                        # Ignore failed deletion here for deleting pool
                        pv.delete_volume(vol)
                if not sp.delete_pool(pool_name):
                    raise error.TestFail("Delete pool %s failed" % pool_name)
        finally:
            if pool_type == "netfs":
                nfs_server_dir = self.params.get("nfs_server_dir", "nfs-server")
                nfs_path = os.path.join(self.tmpdir, nfs_server_dir)
                setup_or_cleanup_nfs(is_setup=False, mount_dir=nfs_path)
                if os.path.exists(nfs_path):
                    shutil.rmtree(nfs_path)
            if pool_type == "logical":
                cmd = "pvs |grep vg_logical|awk '{print $1}'"
                pv = utils.system_output(cmd)
                # Cleanup logical volume anyway
                utils.run("vgremove -f vg_logical", ignore_status=True)
                utils.run("pvremove %s" % pv, ignore_status=True)
            # These types used iscsi device
            if pool_type in ["logical", "iscsi", "fs", "disk", "scsi"]:
                setup_or_cleanup_iscsi(is_setup=False,
                                       emulated_image=emulated_image)
            if pool_type in ["dir", "fs", "netfs"]:
                pool_target = os.path.join(self.tmpdir, pool_target)
                if os.path.exists(pool_target):
                    shutil.rmtree(pool_target)
            if pool_type == "gluster":
                setup_or_cleanup_gluster(False, source_name)

    def pre_pool(self, pool_name, pool_type, pool_target, emulated_image,
                 image_size="100M", pre_disk_vol=[], source_name=None,
                 source_path=None):
        """
        Preapare the specific type pool

        Note:
            1. For scsi type pool, it only could be created from xml file
            2. Other type pools can be created by pool_creat_as function
            3. Disk pool will not allow to create volume with virsh commands
               So we can prepare it before pool created

        :param pool_name: created pool name
        :param pool_type: dir, disk, logical, fs, netfs or else
        :param pool_target: target of storage pool
        :param emulated_image: use an image file to simulate a scsi disk
                               it could be used for disk, logical pool
        :param image_size: the size for emulated image
        :param pre_disk_vol: a list include partition size to be created
                             no more than 4 partition because msdos label
        """
        extra = ""
        if pool_type == "dir":
            logging.info("Pool path:%s", self.tmpdir)
            pool_target = os.path.join(self.tmpdir, pool_target)
            if not os.path.exists(pool_target):
                os.mkdir(pool_target)
        elif pool_type == "disk":
            device_name = setup_or_cleanup_iscsi(is_setup=True,
                                                 emulated_image=emulated_image,
                                                 image_size=image_size)
            # If pre_vol is None, disk pool will have no volume
            if type(pre_disk_vol) == list and len(pre_disk_vol):
                for vol in pre_disk_vol:
                    mk_part(device_name, vol)
            extra = " --source-dev %s" % device_name
        elif pool_type == "fs":
            device_name = setup_or_cleanup_iscsi(is_setup=True,
                                                 emulated_image=emulated_image,
                                                 image_size=image_size)
            cmd = "mkfs.ext4 -F %s" % device_name
            pool_target = os.path.join(self.tmpdir, pool_target)
            if not os.path.exists(pool_target):
                os.mkdir(pool_target)
            extra = " --source-dev %s" % device_name
            utils.run(cmd)
        elif pool_type == "logical":
            logical_device = setup_or_cleanup_iscsi(is_setup=True,
                                                    emulated_image=emulated_image,
                                                    image_size=image_size)
            cmd_pv = "pvcreate %s" % logical_device
            vg_name = "vg_%s" % pool_type
            cmd_vg = "vgcreate %s %s" % (vg_name, logical_device)
            extra = "--source-name %s" % vg_name
            utils.run(cmd_pv)
            utils.run(cmd_vg)
            # Create a small volume for verification
            # And VG path will not exist if no any volume in.(bug?)
            cmd_lv = "lvcreate --name default_lv --size 1M %s" % vg_name
            utils.run(cmd_lv)
        elif pool_type == "netfs":
            nfs_server_dir = self.params.get("nfs_server_dir", "nfs-server")
            nfs_path = os.path.join(self.tmpdir, nfs_server_dir)
            if not os.path.exists(nfs_path):
                os.mkdir(nfs_path)
            pool_target = os.path.join(self.tmpdir, pool_target)
            if not os.path.exists(pool_target):
                os.mkdir(pool_target)
            setup_or_cleanup_nfs(is_setup=True,
                                 export_options="rw,async,no_root_squash",
                                 mount_src=nfs_path)
            source_host = self.params.get("source_host", "localhost")
            extra = "--source-host %s --source-path %s" % (source_host,
                                                           nfs_path)
        elif pool_type == "iscsi":
            setup_or_cleanup_iscsi(is_setup=True,
                                   emulated_image=emulated_image,
                                   image_size=image_size)
            # Verify if expected iscsi device has been set
            iscsi_sessions = iscsi.iscsi_get_sessions()
            iscsi_target = ()
            for iscsi_node in iscsi_sessions:
                if iscsi_node[1].count(emulated_image):
                    # Remove port for pool operations
                    ip_addr = iscsi_node[0].split(":3260")[0]
                    iscsi_device = (ip_addr, iscsi_node[1])
                    break
            if iscsi_device == ():
                raise error.TestFail("No matched iscsi device.")
            if "::" in iscsi_device[0]:
                iscsi_device = ('localhost', iscsi_device[1])
            extra = " --source-host %s  --source-dev %s" % iscsi_device
        elif pool_type == "scsi":
            scsi_xml_file = self.params.get("scsi_xml_file")
            if not os.path.exists(scsi_xml_file):
                scsi_xml_file = os.path.join(self.tmpdir, scsi_xml_file)
                logical_device = setup_or_cleanup_iscsi(is_setup=True,
                                                        emulated_image=emulated_image,
                                                        image_size=image_size)
                cmd = ("iscsiadm -m session -P 3 |grep -B3 %s| grep Host|awk "
                       "'{print $3}'" % logical_device.split('/')[2])
                scsi_host = utils.system_output(cmd)
                scsi_xml = """
<pool type='scsi'>
  <name>%s</name>
   <source>
    <adapter type='scsi_host' name='host%s'/>
  </source>
  <target>
    <path>/dev/disk/by-path</path>
  </target>
</pool>
""" % (pool_name, scsi_host)
                logging.debug("Prepare the scsi pool xml: %s", scsi_xml)
                xml_object = open(scsi_xml_file, 'w')
                xml_object.write(scsi_xml)
                xml_object.close()
        elif pool_type == "gluster":
            # Prepare gluster service and create volume
            hostip = setup_or_cleanup_gluster(True, source_name,
                                              pool_name=pool_name)
            logging.debug("hostip is %s", hostip)
            cleanup_gluster = True
            extra = "--source-host %s --source-path %s --source-name %s" % \
                    (hostip, source_path, source_name)

        # Create pool
        if pool_type == "scsi":
            re_v = virsh.pool_create(scsi_xml_file)
        else:
            re_v = virsh.pool_create_as(pool_name, pool_type,
                                        pool_target, extra)
        if not re_v:
            raise error.TestFail("Create pool failed.")
        # Check the created pool
        check_actived_pool(pool_name)

    def pre_vol(self, vol_name, vol_format, capacity, allocation, pool_name):
        """
        Preapare the specific type volume in pool
        """
        pv = libvirt_storage.PoolVolume(pool_name)
        if not pv.create_volume(vol_name, capacity, allocation, vol_format):
            raise error.TestFail("Prepare volume failed.")
        if not pv.volume_exists(vol_name):
            raise error.TestFail("Can't find volume: %s", vol_name)


##########Migration Relative functions##############
class MigrationTest(object):

    """Class for migration tests"""

    def __init__(self):
        # To get result in thread, using member parameters
        # Result of virsh migrate command
        # True means command executed successfully
        self.RET_MIGRATION = True
        # A lock for threads
        self.RET_LOCK = threading.RLock()
        # The time spent when migrating vms
        # format: vm_name -> time(seconds)
        self.mig_time = {}

    def thread_func_migration(self, vm, desturi, options=None):
        """
        Thread for virsh migrate command.

        :param vm: A libvirt vm instance(local or remote).
        :param desturi: remote host uri.
        """
        # Migrate the domain.
        try:
            if options is None:
                options = "--live --timeout=60"
            stime = int(time.time())
            vm.migrate(desturi, option=options, ignore_status=False,
                       debug=True)
            etime = int(time.time())
            self.mig_time[vm.name] = etime - stime
        except error.CmdError, detail:
            logging.error("Migration to %s failed:\n%s", desturi, detail)
            self.RET_LOCK.acquire()
            self.RET_MIGRATION = False
            self.RET_LOCK.release()

    def do_migration(self, vms, srcuri, desturi, migration_type, options=None,
                     thread_timeout=60):
        """
        Migrate vms.

        :param vms: migrated vms.
        :param srcuri: local uri, used when migrate vm from remote to local
        :param descuri: remote uri, used when migrate vm from local to remote
        :param migration_type: do orderly for simultaneous migration
        """
        if migration_type == "orderly":
            for vm in vms:
                migration_thread = threading.Thread(target=self.thread_func_migration,
                                                    args=(vm, desturi, options))
                migration_thread.start()
                migration_thread.join(thread_timeout)
                if migration_thread.isAlive():
                    logging.error("Migrate %s timeout.", migration_thread)
                    self.RET_LOCK.acquire()
                    self.RET_MIGRATION = False
                    self.RET_LOCK.release()
        elif migration_type == "cross":
            # Migrate a vm to remote first,
            # then migrate another to remote with the first vm back
            vm_remote = vms.pop()
            self.thread_func_migration(vm_remote, desturi)
            for vm in vms:
                thread1 = threading.Thread(target=self.thread_func_migration,
                                           args=(vm_remote, srcuri, options))
                thread2 = threading.Thread(target=self.thread_func_migration,
                                           args=(vm, desturi, options))
                thread1.start()
                thread2.start()
                thread1.join(thread_timeout)
                thread2.join(thread_timeout)
                vm_remote = vm
                if thread1.isAlive() or thread1.isAlive():
                    logging.error("Cross migrate timeout.")
                    self.RET_LOCK.acquire()
                    self.RET_MIGRATION = False
                    self.RET_LOCK.release()
            # Add popped vm back to list
            vms.append(vm_remote)
        elif migration_type == "simultaneous":
            migration_threads = []
            for vm in vms:
                migration_threads.append(threading.Thread(
                                         target=self.thread_func_migration,
                                         args=(vm, desturi, options)))
            # let all migration going first
            for thread in migration_threads:
                thread.start()

            # listen threads until they end
            for thread in migration_threads:
                thread.join(thread_timeout)
                if thread.isAlive():
                    logging.error("Migrate %s timeout.", thread)
                    self.RET_LOCK.acquire()
                    self.RET_MIGRATION = False
                    self.RET_LOCK.release()

        if not self.RET_MIGRATION:
            raise error.TestFail()

    def cleanup_dest_vm(self, vm, srcuri, desturi):
        """
        Cleanup migrated vm on remote host.
        """
        vm.connect_uri = desturi
        if vm.exists():
            if vm.is_persistent():
                vm.undefine()
            if vm.is_alive():
                # If vm on remote host is unaccessible
                # graceful shutdown may cause confused
                vm.destroy(gracefully=False)
        # Set connect uri back to local uri
        vm.connect_uri = srcuri


def check_exit_status(result, expect_error=False):
    """
    Check the exit status of virsh commands.

    :param result: Virsh command result object
    :param expect_error: Boolean value, expect command success or fail
    """
    if not expect_error:
        if result.exit_status != 0:
            raise error.TestFail(result.stderr)
        else:
            logging.debug("Command output:\n%s", result.stdout.strip())
    elif expect_error and result.exit_status == 0:
        raise error.TestFail("Expect fail, but run successfully.")


def check_iface(iface_name, checkpoint, extra=""):
    """
    Check interface with specified checkpoint.

    :param iface_name: Interface name
    :param checkpoint: Check if interface exists, MAC address, IP address or
                       ping out. Support values: [exists, mac, ip, ping]
    :param extra: Extra string for checking
    :return: Boolean value, true for pass, false for fail
    """
    support_check = ["exists", "mac", "ip", "ping"]
    iface = utils_net.Interface(name=iface_name)
    check_pass = False
    try:
        if checkpoint == "exists":
            # extra is iface-list option
            list_find, ifcfg_find = (False, False)
            # Check virsh list output
            result = virsh.iface_list(extra, ignore_status=True)
            check_exit_status(result, False)
            output = re.findall(r"(\S+)\ +(\S+)\ +(\S+|\s+)[\ +\n]",
                                str(result.stdout))
            if filter(lambda x: x[0] == iface_name, output[1:]):
                list_find = True
            logging.debug("Find '%s' in virsh iface-list output: %s",
                          iface_name, list_find)
            # Check network script
            iface_script = "/etc/sysconfig/network-scripts/ifcfg-" + iface_name
            ifcfg_find = os.path.exists(iface_script)
            logging.debug("Find '%s': %s", iface_script, ifcfg_find)
            check_pass = list_find and ifcfg_find
        elif checkpoint == "mac":
            # extra is the MAC address to compare
            iface_mac = iface.get_mac().lower()
            check_pass = iface_mac == extra
            logging.debug("MAC address of %s: %s", iface_name, iface_mac)
        elif checkpoint == "ip":
            # extra is the IP address to compare
            iface_ip = iface.get_ip()
            check_pass = iface_ip == extra
            logging.debug("IP address of %s: %s", iface_name, iface_ip)
        elif checkpoint == "ping":
            # extra is the ping destination
            ping_s, _ = ping(dest=extra, count=3, interface=iface_name,
                             timeout=5,)
            check_pass = ping_s == 0
        else:
            logging.debug("Support check points are: %s", support_check)
            logging.error("Unsupport check point: %s", checkpoint)
    except Exception, detail:
        raise error.TestFail("Interface check failed: %s" % detail)
    return check_pass


def create_disk_xml(params):
    """
    Create a disk configuration file.
    """
    # Create attributes dict for disk's address element
    type_name = params.get("type_name", "file")
    source_file = params.get("source_file")
    target_dev = params.get("target_dev", "vdb")
    target_bus = params.get("target_bus", "virtio")
    diskxml = disk.Disk(type_name)
    diskxml.device = params.get("device_type", "disk")
    if type_name == "file":
        source_type = "file"
    else:
        source_type = "dev"
    diskxml.source = diskxml.new_disk_source(attrs={source_type: source_file})
    diskxml.target = {'dev': target_dev, 'bus': target_bus}
    logging.debug("Disk XML:\n%s", str(diskxml))
    return diskxml.xml


def attach_additional_device(vm_name, targetdev, disk_path, params):
    """
    Create a disk with disksize, then attach it to given vm.

    :param vm_name: Libvirt VM name.
    :param disk_path: path of attached disk
    :param targetdev: target of disk device
    :param params: dict include necessary configurations of device
    """
    logging.info("Attaching disk...")

    # Update params for source file
    params['source_file'] = disk_path
    params['target_dev'] = targetdev

    # Create a file of device
    xmlfile = create_disk_xml(params)

    # To confirm attached device do not exist.
    virsh.detach_disk(vm_name, targetdev, extra="--config")

    return virsh.attach_device(domain_opt=vm_name, file_opt=xmlfile,
                               flagstr="--config", debug=True)


def device_exists(vm, target_dev):
    """
    Check if given target device exists on vm.
    """
    targets = vm.get_blk_devices().keys()
    if target_dev in targets:
        return True
    return False


def create_local_disk(disk_type, path=None, size=10,
                      vgname=None, lvname=None):
    if disk_type == "file":
        utils.run("mkdir -p %s" % os.path.dirname(path))
        cmd = "qemu-img create %s %sG" % (path, size)
    else:
        cmd = "lvcreate -V %sG %s --name %s --size 1M" % (size,
                                                          vgname,
                                                          lvname)
        path = "/dev/%s/%s" % (vgname, lvname)
    result = utils.run(cmd, ignore_status=True)
    if result.exit_status:
        raise error.TestFail("Create image '%s' on local host failed." % path)
    else:
        return path


def delete_local_disk(disk_type, path=None):
    if disk_type == "file":
        cmd = "rm -f %s" % path
    else:
        cmd = "lvremove -f %s" % path
    utils.run(cmd, ignore_status=True)


def attach_disks(vm, path, vgname, params):
    """
    Attach multiple disks.According parameter disk_type in params,
    it will create lvm or file type disks.

    :param path: file type disk's path
    :param vgname: lvm type disk's volume group name
    """
    # Additional disk on vm
    disks_count = int(params.get("added_disks_count", 1)) - 1
    disk_size = params.get("added_disk_size", "0.1")
    disk_type = params.get("added_disk_type", "file")
    target_list = []
    index = 0
    while len(target_list) < disks_count:
        target_dev = "vd%s" % chr(ord('a') + index)
        if not device_exists(vm, target_dev):
            target_list.append(target_dev)
        index += 1

    # A dict include disks information: source file and size
    added_disks = {}
    for target_dev in target_list:
        disk_params = {}
        disk_params['type_name'] = disk_type
        device_name = "%s_%s" % (target_dev, vm.name)
        disk_path = os.path.join(os.path.dirname(path), device_name)
        disk_path = create_local_disk(disk_type,
                                      disk_path, disk_size,
                                      vgname, device_name)
        added_disks[disk_path] = disk_size
        result = attach_additional_device(vm.name,
                                          target_dev, disk_path, disk_params)
        if result.exit_status:
            raise error.TestFail("Attach device %s failed."
                                 % target_dev)
    logging.debug("New VM XML:\n%s", vm.get_xml())
    return added_disks


def define_new_vm(vm_name, new_name):
    """
    Just define a new vm from given name
    """
    try:
        vmxml = vm_xml.VMXML.new_from_dumpxml(vm_name)
        vmxml.vm_name = new_name
        del vmxml.uuid
        vmxml.define()
        return True
    except xcepts.LibvirtXMLError, detail:
        logging.error(detail)
        return False
