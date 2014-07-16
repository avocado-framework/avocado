import re
import os
import logging
import commands
from autotest.client.shared import error, utils
from virttest import virsh, virt_vm, libvirt_vm, data_dir
from virttest import utils_net, xml_utils
from virttest.libvirt_xml import vm_xml, xcepts
from virttest import utils_libguestfs as lgf
from virttest import qemu_storage


class VTError(Exception):
    pass


class VTAttachError(VTError):

    def __init__(self, cmd, output):
        super(VTAttachError, self).__init__(cmd, output)
        self.cmd = cmd
        self.output = output

    def __str__(self):
        return ("Attach command failed:%s\n%s" % (self.cmd, self.output))


class VTMountError(VTError):

    def __init__(self, cmd, output):
        VTError.__init__(self, cmd, output)
        self.cmd = cmd
        self.output = output

    def __str__(self):
        return ("Mount command failed:%s\n%s" % (self.cmd, self.output))


class VTXMLParseError(VTError):

    def __init__(self, cmd, output):
        super(VTXMLParseError, self).__init__(cmd, output)
        self.cmd = cmd
        self.output = output

    def __str__(self):
        return ("Parse XML with '%s' failed:%s" % (self.cmd, self.output))


def preprocess_image(params):
    """
    Create a disk which used by guestfish

    params: Get params from cfg file
    """
    image_dir = params.get("img_dir", data_dir.get_tmp_dir())
    image_name = params.get("image_name", "gs_common")
    image = qemu_storage.QemuImg(params, image_dir, image_name)
    image_path, _ = image.create(params)

    logging.info("Image created in %s" % image_path)
    return image_path


def primary_disk_virtio(vm):
    """
    To verify if system disk is virtio.

    :param vm: Libvirt VM object.
    """
    vmdisks = vm.get_disk_devices()
    if "vda" in vmdisks.keys():
        return True
    return False


def get_primary_disk(vm):
    """
    Get primary disk source.

    :param vm: Libvirt VM object.
    """
    vmdisks = vm.get_disk_devices()
    if len(vmdisks):
        pri_target = ['vda', 'sda']
        for target in pri_target:
            try:
                return vmdisks[target]['source']
            except KeyError:
                pass
    return None


def attach_additional_disk(vm, disksize, targetdev):
    """
    Create a disk with disksize, then attach it to given vm.

    :param vm: Libvirt VM object.
    :param disksize: size of attached disk
    :param targetdev: target of disk device
    """
    logging.info("Attaching disk...")
    disk_path = os.path.join(data_dir.get_tmp_dir(), targetdev)
    cmd = "qemu-img create %s %s" % (disk_path, disksize)
    status, output = commands.getstatusoutput(cmd)
    if status:
        return (False, output)

    # To confirm attached device do not exist.
    virsh.detach_disk(vm.name, targetdev, extra="--config")

    attach_result = virsh.attach_disk(vm.name, disk_path, targetdev,
                                      extra="--config", debug=True)
    if attach_result.exit_status:
        return (False, attach_result)
    return (True, disk_path)


def define_new_vm(vm_name, new_name):
    """
    Just define a new vm from given name
    """
    try:
        vmxml = vm_xml.VMXML.new_from_dumpxml(vm_name)
        vmxml.vm_name = new_name
        del vmxml.uuid
        logging.debug(str(vmxml))
        vmxml.define()
        return True
    except xcepts.LibvirtXMLError, detail:
        logging.error(detail)
        return False


def cleanup_vm(vm_name=None, disk=None):
    """
    Cleanup the vm with its disk deleted.
    """
    try:
        if vm_name is not None:
            virsh.undefine(vm_name)
    except error.CmdError, detail:
        logging.error("Undefine %s failed:%s", vm_name, detail)
    try:
        if disk is not None:
            os.remove(disk)
    except IOError, detail:
        logging.error("Remove disk %s failed:%s", disk, detail)


class VirtTools(object):

    """
    Useful functions for virt-commands.

    Some virt-tools need an input disk and output disk.
    Main for virt-clone, virt-sparsify, virt-resize.
    """

    def __init__(self, vm, params):
        self.params = params
        self.oldvm = vm
        # Many command will create a new vm or disk, init it here
        self.newvm = libvirt_vm.VM("VTNEWVM", vm.params, vm.root_dir,
                                   vm.address_cache)
        # Preapre for created vm disk
        self.indisk = get_primary_disk(vm)
        self.outdisk = None

    def update_vm_disk(self):
        """
        Update oldvm's disk, and then create a newvm.
        """
        target_dev = self.params.get("gf_updated_target_dev", "vdb")
        device_size = self.params.get("gf_updated_device_size", "50M")
        self.newvm.name = self.params.get("gf_updated_new_vm")
        if self.newvm.is_alive():
            self.newvm.destroy()
            self.newvm.wait_for_shutdown()

        attachs, attacho = attach_additional_disk(self.newvm,
                                                  disksize=device_size,
                                                  targetdev=target_dev)
        if attachs:
            # Restart vm for guestfish command
            # Otherwise updated disk is not visible
            try:
                self.newvm.start()
                self.newvm.wait_for_login()
                self.newvm.destroy()
                self.newvm.wait_for_shutdown()
                self.params['added_disk_path'] = attacho
            except virt_vm.VMError, detail:
                raise VTAttachError("", str(detail))
        else:
            raise VTAttachError("", attacho)

    def clone_vm_filesystem(self, newname=None):
        """
        Clone a new vm with only its filesystem disk.

        :param newname:if newname is None,
                       create a new name with clone added.
        """
        logging.info("Cloning...")
        # Init options for virt-clone
        options = {}
        autoclone = bool(self.params.get("autoclone", False))
        new_filesystem_path = self.params.get("new_filesystem_path")
        cloned_files = []
        if new_filesystem_path:
            self.outdisk = new_filesystem_path
        elif self.indisk is not None:
            self.outdisk = "%s-clone" % self.indisk
        cloned_files.append(self.outdisk)
        options['files'] = cloned_files
        # cloned_mac can be CREATED, RANDOM or a string.
        cloned_mac = self.params.get("cloned_mac", "CREATED")
        if cloned_mac == "CREATED":
            options['mac'] = utils_net.generate_mac_address_simple()
        else:
            options['mac'] = cloned_mac

        options['ignore_status'] = True
        options['debug'] = True
        options['timeout'] = int(self.params.get("timeout", 240))
        if newname is None:
            newname = "%s-virtclone" % self.oldvm.name
        result = lgf.virt_clone_cmd(self.oldvm.name, newname,
                                    autoclone, **options)
        if result.exit_status:
            error_info = "Clone %s to %s failed." % (self.oldvm.name, newname)
            logging.error(error_info)
            return (False, result)
        else:
            self.newvm.name = newname
            cloned_mac = vm_xml.VMXML.get_first_mac_by_name(newname)
            if cloned_mac is not None:
                self.newvm.address_cache[cloned_mac] = None
            return (True, result)

    def sparsify_disk(self):
        """
        Sparsify a disk
        """
        logging.info("Sparsifing...")
        if self.indisk is None:
            logging.error("No disk can be sparsified.")
            return (False, "Input disk is None.")
        if self.outdisk is None:
            self.outdisk = "%s-sparsify" % self.indisk
        timeout = int(self.params.get("timeout", 240))
        result = lgf.virt_sparsify_cmd(self.indisk, self.outdisk,
                                       ignore_status=True, debug=True,
                                       timeout=timeout)
        if result.exit_status:
            error_info = "Sparsify %s to %s failed." % (self.indisk,
                                                        self.outdisk)
            logging.error(error_info)
            return (False, result)
        return (True, result)

    def define_vm_with_newdisk(self):
        """
        Define the new vm with old vm's configuration

        Changes:
        1.replace name
        2.delete uuid
        3.replace disk
        """
        logging.info("Define a new vm:")
        old_vm_name = self.oldvm.name
        new_vm_name = "%s-vtnewdisk" % old_vm_name
        self.newvm.name = new_vm_name
        old_disk = self.indisk
        new_disk = self.outdisk
        try:
            vmxml = vm_xml.VMXML.new_from_dumpxml(old_vm_name)
            vmxml.vm_name = new_vm_name
            vmxml.uuid = ""
            vmxml.set_xml(re.sub(old_disk, new_disk,
                                 str(vmxml.__dict_get__('xml'))))
            logging.debug(vmxml.__dict_get__('xml'))
            vmxml.define()
        except xcepts.LibvirtXMLError, detail:
            logging.debug(detail)
            return (False, detail)
        return (True, vmxml.xml)

    def expand_vm_filesystem(self, resize_part_num=2, resized_size="+1G",
                             new_disk=None):
        """
        Expand vm's filesystem with virt-resize.
        """
        logging.info("Resizing vm's disk...")
        options = {}
        options['resize'] = "/dev/sda%s" % resize_part_num
        options['resized_size'] = resized_size
        if new_disk is not None:
            self.outdisk = new_disk
        elif self.outdisk is None:
            self.outdisk = "%s-resize" % self.indisk

        options['ignore_status'] = True
        options['debug'] = True
        options['timeout'] = int(self.params.get("timeout", 480))
        result = lgf.virt_resize_cmd(self.indisk, self.outdisk, **options)
        if result.exit_status:
            logging.error(result)
            return (False, result)
        return (True, self.outdisk)

    def guestmount(self, mountpoint, disk_or_domain=None):
        """
        Mount filesystems in a disk or domain to host mountpoint.

        :param disk_or_domain: if it is None, use default vm in params
        """
        logging.info("Mounting filesystems...")
        if disk_or_domain is None:
            disk_or_domain = self.oldvm.name
        if not os.path.isdir(mountpoint):
            os.mkdir(mountpoint)
        if os.path.ismount(mountpoint):
            utils.run("umount -l %s" % mountpoint, ignore_status=True)
        inspector = "yes" == self.params.get("gm_inspector", "yes")
        readonly = "yes" == self.params.get("gm_readonly", "no")
        special_mountpoints = self.params.get("special_mountpoints", [])
        is_disk = "yes" == self.params.get("gm_is_disk", "no")
        options = {}
        options['ignore_status'] = True
        options['debug'] = True
        options['timeout'] = int(self.params.get("timeout", 240))
        options['special_mountpoints'] = special_mountpoints
        options['is_disk'] = is_disk
        result = lgf.guestmount(disk_or_domain, mountpoint,
                                inspector, readonly, **options)
        if result.exit_status:
            error_info = "Mount %s to %s failed." % (disk_or_domain,
                                                     mountpoint)
            logging.error(result)
            return (False, error_info)
        return (True, mountpoint)

    def write_file_with_guestmount(self, mountpoint, path,
                                   content=None, vm_ref=None,
                                   cleanup=True):
        """
        Write content to file with guestmount
        """
        logging.info("Creating file...")
        gms, gmo = self.guestmount(mountpoint, vm_ref)
        if gms is True:
            mountpoint = gmo
        else:
            logging.error("Create file %s failed.", path)
            return (False, gmo)

        # file's path on host's mountpoint
        file_path = os.path.join(mountpoint, path)
        if content is None:
            content = "This is a temp file with guestmount."
        try:
            fd = open(file_path, "w")
            fd.write(content)
            fd.close()
        except IOError, detail:
            logging.error(detail)
            return (False, detail)
        logging.info("Create file %s successfully", file_path)
        # Cleanup created file
        if cleanup:
            utils.run("rm -f %s" % file_path, ignore_status=True)
        return (True, file_path)

    def get_primary_disk_fs_type(self):
        """
        Get primary disk filesystem type
        """
        result = lgf.virt_filesystems(self.oldvm.name, long_format=True)
        if result.exit_status:
            raise error.TestNAError("Cannot get primary disk"
                                    " filesystem information!")
        fs_info = result.stdout.strip().splitlines()
        if len(fs_info) <= 1:
            raise error.TestNAError("No disk filesystem information!")
        try:
            primary_disk_info = fs_info[1]
            fs_type = primary_disk_info.split()[2]
            return fs_type
        except (KeyError, ValueError), detail:
            raise error.TestFail(str(detail))

    def tar_in(self, tar_file, dest="/tmp", vm_ref=None):
        if vm_ref is None:
            vm_ref = self.oldvm.name
        result = lgf.virt_tar_in(vm_ref, tar_file, dest,
                                 debug=True, ignore_status=True)
        return result

    def tar_out(self, directory, tar_file="temp.tar", vm_ref=None):
        if vm_ref is None:
            vm_ref = self.oldvm.name
        result = lgf.virt_tar_out(vm_ref, directory, tar_file,
                                  debug=True, ignore_status=True)
        return result

    def cat(self, filename, vm_ref=None):
        if vm_ref is None:
            vm_ref = self.oldvm.name
        result = lgf.virt_cat_cmd(vm_ref, filename, debug=True,
                                  ignore_status=True)
        return result

    def copy_in(self, filename, dest="/tmp", vm_ref=None):
        if vm_ref is None:
            vm_ref = self.oldvm.name
        result = lgf.virt_copy_in(vm_ref, filename, dest, debug=True,
                                  ignore_status=True)
        return result

    def copy_out(self, file_path, localdir="/tmp", vm_ref=None):
        if vm_ref is None:
            vm_ref = self.oldvm.name
        result = lgf.virt_copy_out(vm_ref, file_path, localdir,
                                   debug=True, ignore_status=True)
        return result

    def format_disk(self, disk_path=None, filesystem=None, partition=None,
                    lvm=None):
        """
        :param disk_path: None for additional disk by update_vm_disk() only
        """
        if disk_path is None:
            disk_path = self.params.get("added_disk_path")
        result = lgf.virt_format(disk_path, filesystem,
                                 lvm=lvm, partition=partition,
                                 debug=True, ignore_status=True)
        return result

    def get_filesystems_info(self, vm_ref=None):
        if vm_ref is None:
            vm_ref = self.oldvm.name
        result = lgf.virt_filesystems(vm_ref, long_format=True,
                                      debug=True, all=True,
                                      ignore_status=True)
        return result

    def list_df(self, vm_ref=None):
        if vm_ref is None:
            vm_ref = self.oldvm.name
        result = lgf.virt_df(vm_ref, debug=True, ignore_status=True)
        return result

    def get_vm_info_with_inspector(self, vm_ref=None):
        """
        Return a dict includes os information.
        """
        if vm_ref is None:
            vm_ref = self.oldvm.name
        # A dict to include system information
        sys_info = {}
        result = lgf.virt_inspector(vm_ref, ignore_status=True)
        if result.exit_status:
            logging.error("Get %s information with inspector(2) failed:\n%s",
                          vm_ref, result)
            return sys_info
        # Analyse output to get information
        try:
            xmltreefile = xml_utils.XMLTreeFile(result.stdout)
            os_root = xmltreefile.find("operatingsystem")
            if os_root is None:
                raise VTXMLParseError("operatingsystem", os_root)
        except (IOError, VTXMLParseError), detail:
            logging.error(detail)
            return sys_info
        sys_info['root'] = os_root.findtext("root")
        sys_info['name'] = os_root.findtext("name")
        sys_info['arch'] = os_root.findtext("arch")
        sys_info['distro'] = os_root.findtext("distro")
        sys_info['release'] = os_root.findtext("product_name")
        sys_info['major_version'] = os_root.findtext("major_version")
        sys_info['minor_version'] = os_root.findtext("minor_version")
        sys_info['hostname'] = os_root.findtext("hostname")
        # filesystems and mountpoints are dict to restore detail info
        mountpoints = {}
        for node in os_root.find("mountpoints"):
            mp_device = node.get("dev")
            if mp_device is not None:
                mountpoints[mp_device] = node.text
        sys_info['mountpoints'] = mountpoints
        filesystems = {}
        for node in os_root.find("filesystems"):
            fs_detail = {}
            fs_device = node.get("dev")
            if fs_device is not None:
                fs_detail['type'] = node.findtext("type")
                fs_detail['label'] = node.findtext("label")
                fs_detail['uuid'] = node.findtext("uuid")
                filesystems[fs_device] = fs_detail
        sys_info['filesystems'] = filesystems
        logging.debug("VM information:\n%s", sys_info)
        return sys_info


class GuestfishTools(lgf.GuestfishPersistent):

    """Useful Tools for Guestfish class."""

    __slots__ = ('params', )

    def __init__(self, params):
        """
        Init a persistent guestfish shellsession.
        """
        self.params = params
        disk_img = params.get("disk_img")
        ro_mode = bool(params.get("gf_ro_mode", False))
        libvirt_domain = params.get("libvirt_domain")
        inspector = bool(params.get("gf_inspector", False))
        mount_options = params.get("mount_options")
        run_mode = params.get("gf_run_mode", "interactive")
        super(GuestfishTools, self).__init__(disk_img, ro_mode,
                                             libvirt_domain, inspector,
                                             mount_options=mount_options,
                                             run_mode=run_mode)

    def get_root(self):
        """
        Get root filesystem w/ guestfish
        """
        getroot_result = self.inspect_os()
        roots_list = getroot_result.stdout.splitlines()
        if getroot_result.exit_status or not len(roots_list):
            logging.error("Get root failed:%s", getroot_result)
            return (False, getroot_result)
        return (True, roots_list[0].strip())

    def analyse_release(self):
        """
        Analyse /etc/redhat-release
        """
        logging.info("Analysing /etc/redhat-release...")
        release_result = self.cat("/etc/redhat-release")
        logging.debug(release_result)
        if release_result.exit_status:
            logging.error("Cat /etc/redhat-release failed")
            return (False, release_result)

        release_type = {'rhel': "Red Hat Enterprise Linux",
                        'fedora': "Fedora"}
        for key in release_type:
            if re.search(release_type[key], release_result.stdout):
                return (True, key)

    def write_file(self, path, content):
        """
        Create a new file to vm with guestfish
        """
        logging.info("Creating file %s in vm...", path)
        write_result = self.write(path, content)
        if write_result.exit_status:
            logging.error("Create '%s' with content '%s' failed:%s",
                          path, content, write_result)
            return False
        return True

    def get_partitions_info(self, device="/dev/sda"):
        """
        Get disk partition's information.
        """
        list_result = self.part_list(device)
        if list_result.exit_status:
            logging.error("List partition info failed:%s", list_result)
            return (False, list_result)
        list_lines = list_result.stdout.splitlines()
        # This dict is a struct like this: {key:{a dict}, key:{a dict}}
        partitions = {}
        # This dict is a struct of normal dict, for temp value of a partition
        part_details = {}
        index = -1
        for line in list_lines:
            # Init for a partition
            if re.search("\[\d\]\s+=", line):
                index = line.split("]")[0].split("[")[-1]
                part_details = {}
                partitions[index] = part_details

            if re.search("part_num", line):
                part_num = int(line.split(":")[-1].strip())
                part_details['num'] = part_num
            elif re.search("part_start", line):
                part_start = int(line.split(":")[-1].strip())
                part_details['start'] = part_start
            elif re.search("part_end", line):
                part_end = int(line.split(":")[-1].strip())
                part_details['end'] = part_end
            elif re.search("part_size", line):
                part_size = int(line.split(":")[-1].strip())
                part_details['size'] = part_size

            if index != -1:
                partitions[index] = part_details
        logging.info(partitions)
        return (True, partitions)

    def get_part_size(self, part_num):
        status, partitions = self.get_partitions_info()
        if status is False:
            return None
        for partition in partitions.values():
            if str(partition.get("num")) == str(part_num):
                return partition.get("size")

    def create_fs(self):
        """
        Create filesystem of disk

        Choose lvm or physical partition and create fs on it
        """
        image_path = self.params.get("image_path")
        self.add_drive(image_path)
        self.run()

        partition_type = self.params.get("partition_type")
        fs_type = self.params.get("fs_type", "ext3")
        image_size = self.params.get("image_size", "6G")
        with_blocksize = self.params.get("with_blocksize")
        blocksize = self.params.get("blocksize")
        tarball_path = self.params.get("tarball_path")

        if partition_type not in ['lvm', 'physical']:
            return (False, "partition_type is incorrect, support [physical,lvm]")

        if partition_type == "lvm":
            logging.info("create lvm partition...")
            pv_name = self.params.get("pv_name", "/dev/sdb")
            vg_name = self.params.get("vg_name", "vol_test")
            lv_name = self.params.get("lv_name", "vol_file")
            mount_point = "/dev/%s/%s" % (vg_name, lv_name)
            lv_size = int(image_size.replace('G', '')) * 1000

            self.pvcreate(pv_name)
            self.vgcreate(vg_name, pv_name)
            self.lvcreate(lv_name, vg_name, lv_size)

        elif partition_type == "physical":
            logging.info("create physical partition...")
            pv_name = self.params.get("pv_name", "/dev/sdb")
            mount_point = pv_name + "1"

            self.part_disk(pv_name, "mbr")
            self.part_list(pv_name)

        self.params["mount_point"] = mount_point
        if with_blocksize == "yes" and fs_type != "btrfs":
            if blocksize:
                self.mkfs_opts(fs_type, mount_point, "blocksize:%s" % (blocksize))
                self.vfs_type(mount_point)
            else:
                logging.error("with_blocksize is set but blocksize not given")
                self.umount_all()
                self.sync()
                return (False, "with_blocksize is set but blocksize not given")
        else:
            self.mkfs(fs_type, mount_point)
            self.vfs_type(mount_point)

        if tarball_path:
            self.mount_options("noatime", mount_point, '/')
            self.tar_in_opts(tarball_path, '/', 'gzip')
            self.ll('/')

        self.umount_all()
        self.sync()
        return (True, "create_fs successfully")

    def create_msdos_part(self, device, start="1", end="-1"):
        """
        Create a msdos partition in given device.
        Default partition section is whole disk(1~-1).
        And return its part name if part add succeed.
        """
        logging.info("Creating a new partition on %s...", device)
        init_result = self.part_init(device, "msdos")
        if init_result.exit_status:
            logging.error("Init disk failed:%s", init_result)
            return (False, init_result)
        add_result = self.part_add(device, "p", start, end)
        if add_result.exit_status:
            logging.error("Add a partition failed:%s", add_result)
            return (False, add_result)

        # Get latest created part num to return
        status, partitions = self.get_partitions_info(device)
        if status is False:
            return (False, partitions)
        part_num = -1
        for partition in partitions.values():
            cur_num = partition.get("num")
            if cur_num > part_num:
                part_num = cur_num

        if part_num == -1:
            return (False, partitions)

        return (True, part_num)

    def create_whole_disk_msdos_part(self, device):
        """
        Create only one msdos partition in given device.
        And return its part name if part add succeed.
        """
        logging.info("Creating one partition of whole %s...", device)
        init_result = self.part_init(device, "msdos")
        if init_result.exit_status:
            logging.error("Init disk failed:%s", init_result)
            return (False, init_result)
        disk_result = self.part_disk(device, "msdos")
        if disk_result.exit_status:
            logging.error("Init disk failed:%s", disk_result)
            return (False, disk_result)

        # Get latest created part num to return
        status, partitions = self.get_partitions_info(device)
        if status is False:
            return (False, partitions)
        part_num = -1
        for partition in partitions.values():
            cur_num = partition.get("num")
            if cur_num > part_num:
                part_num = cur_num

        if part_num == -1:
            return (False, partitions)

        return (True, part_num)

    def get_bootable_part(self, device="/dev/sda"):
        status, partitions = self.get_partitions_info(device)
        if status is False:
            return (False, partitions)
        for partition in partitions.values():
            num = partition.get("num")
            ba_result = self.part_get_bootable(device, num)
            if ba_result.stdout.strip() == "true":
                return (True, "%s%s" % (device, num))
        return (False, partitions)

    def get_mbr_id(self, device="/dev/sda"):
        status, partitions = self.get_partitions_info(device)
        if status is False:
            return (False, partitions)
        for partition in partitions.values():
            num = partition.get("num")
            mbr_id_result = self.part_get_mbr_id(device, num)
            if mbr_id_result.exit_status == 0:
                return (True, mbr_id_result.stdout.strip())
        return (False, partitions)

    def get_part_type(self, device="/dev/sda"):
        part_type_result = self.part_get_parttype(device)
        if part_type_result.exit_status:
            return (False, part_type_result)
        return (True, part_type_result.stdout.strip())

    def get_md5(self, path):
        """
        Get files md5 value.
        """
        logging.info("Computing %s's md5...", path)
        md5_result = self.checksum("md5", path)
        if md5_result.exit_status:
            logging.error("Check %s's md5 failed:%s", path, md5_result)
            return (False, md5_result)
        return (True, md5_result.stdout.strip())

    def reset_interface(self, iface_mac):
        """
        Check interface through guestfish.Fix mac if necessary.
        """
        # disk or domain
        vm_ref = self.params.get("libvirt_domain")
        if not vm_ref:
            vm_ref = self.params.get("disk_img")
            if not vm_ref:
                logging.error("No object to edit.")
                return False
        logging.info("Resetting %s's mac to %s", vm_ref, iface_mac)

        # Fix file which includes interface devices information
        # Default is /etc/udev/rules.d/70-persistent-net.rules
        devices_file = "/etc/udev/rules.d/70-persistent-net.rules"
        # Set file which binds mac and IP-address
        ifcfg_files = ["/etc/sysconfig/network-scripts/ifcfg-p1p1",
                       "/etc/sysconfig/network-scripts/ifcfg-eth0"]
        # Fix devices file
        mac_regex = (r"\w.:\w.:\w.:\w.:\w.:\w.")
        edit_expr = "s/%s/%s/g" % (mac_regex, iface_mac)
        file_ret = self.is_file(devices_file)
        if file_ret.stdout.strip() == "true":
            self.close_session()
            try:
                result = lgf.virt_edit_cmd(vm_ref, devices_file,
                                           expr=edit_expr, debug=True,
                                           ignore_status=True)
                if result.exit_status:
                    logging.error("Edit %s failed:%s", devices_file, result)
                    return False
            except lgf.LibguestfsCmdError, detail:
                logging.error("Edit %s failed:%s", devices_file, detail)
                return False
            self.new_session()
            # Just to keep output looking better
            self.is_ready()
            logging.debug(self.cat(devices_file))

        # Fix interface file
        for ifcfg_file in ifcfg_files:
            file_ret = self.is_file(ifcfg_file)
            if file_ret.stdout.strip() == "false":
                continue
            self.close_session()
            self.params['ifcfg_file'] = ifcfg_file
            try:
                result = lgf.virt_edit_cmd(vm_ref, ifcfg_file,
                                           expr=edit_expr, debug=True,
                                           ignore_status=True)
                if result.exit_status:
                    logging.error("Edit %s failed:%s", ifcfg_file, result)
                    return False
            except lgf.LibguestfsCmdError, detail:
                logging.error("Edit %s failed:%s", ifcfg_file, detail)
                return False
            self.new_session()
            # Just to keep output looking better
            self.is_ready()
            logging.debug(self.cat(ifcfg_file))
        return True

    def copy_ifcfg_back(self):
        # This function must be called after reset_interface()
        ifcfg_file = self.params.get("ifcfg_file")
        bak_file = "%s.bak" % ifcfg_file
        if ifcfg_file:
            self.is_ready()
            is_need = self.is_file(ifcfg_file)
            if is_need.stdout.strip() == "false":
                cp_result = self.cp(bak_file, ifcfg_file)
                if cp_result.exit_status:
                    logging.warn("Recover ifcfg file failed:%s", cp_result)
                    return False
        return True
