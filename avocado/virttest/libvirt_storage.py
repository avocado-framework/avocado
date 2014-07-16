"""
Classes and functions to handle block/disk images for libvirt.

This exports:
  - two functions for get image/blkdebug filename
  - class for image operates and basic parameters
  - class for storage pool operations
"""

import re
import logging
import time
from autotest.client.shared import error
import storage
import virsh


class QemuImg(storage.QemuImg):

    """
    libvirt class for handling operations of disk/block images.
    """

    def __init__(self, params, root_dir, tag):
        """
        Init the default value for image object.

        :param params: Dictionary containing the test parameters.
        :param root_dir: Base directory for relative filenames.
        :param tag: Image tag defined in parameter images.
        """
        storage.QemuImg(params, root_dir, tag)
        # Please init image_cmd for libvirt in this class
        # self.image_cmd =

    def create(self, params):
        """
        Create an image.

        :param params: Dictionary containing the test parameters.

        :note: params should contain:
        """
        raise NotImplementedError

    def convert(self, params, root_dir):
        """
        Convert image

        :param params: A dict
        :param root_dir: dir for save the convert image

        :note: params should contain:
        """
        raise NotImplementedError

    def rebase(self, params):
        """
        Rebase image

        :param params: A dict

        :note: params should contain:
        """
        raise NotImplementedError

    def commit(self):
        """
        Commit image to it's base file
        """
        raise NotImplementedError

    def snapshot_create(self):
        """
        Create a snapshot image.

        :note: params should contain:
        """
        raise NotImplementedError

    def snapshot_del(self, blkdebug_cfg=""):
        """
        Delete a snapshot image.

        :param blkdebug_cfg: The configure file of blkdebug

        :note: params should contain:
               snapshot_image_name -- the name of snapshot image file
        """
        raise NotImplementedError

    def remove(self):
        """
        Remove an image file.

        :note: params should contain:
        """
        raise NotImplementedError

    def check_image(self, params, root_dir):
        """
        Check an image using the appropriate tools for each virt backend.

        :param params: Dictionary containing the test parameters.
        :param root_dir: Base directory for relative filenames.

        :note: params should contain:

        :raise VMImageCheckError: In case qemu-img check fails on the image.
        """
        raise NotImplementedError


class StoragePool(object):

    """
    Pool Manager for libvirt storage with virsh commands
    """

    def __init__(self, virsh_instance=virsh):
        # An instance of Virsh class
        # Help to setup connection to virsh instance
        self.virsh_instance = virsh_instance

    def list_pools(self):
        """
        Return a dict include pools' information with structure:
            pool_name ==> pool_details(a dict: feature ==> value)
        """
        # Allow it raise exception if command has executed failed.
        result = self.virsh_instance.pool_list("--all", ignore_status=False)
        pools = {}
        lines = result.stdout.strip().splitlines()
        if len(lines) > 2:
            head = lines[0]
            lines = lines[2:]
        else:
            return pools

        for line in lines:
            details = line.split()
            details_dict = {}
            head_iter = enumerate(head.split())
            while True:
                try:
                    (index, column) = head_iter.next()
                except StopIteration:
                    break
                if re.match("[N|n]ame", column):
                    pool_name = details[index]
                else:
                    details_dict[column] = details[index]
            pools[pool_name] = details_dict
        return pools

    def pool_exists(self, name):
        """
        Check whether pool exists on given libvirt
        """
        try:
            pools = self.list_pools()
        except error.CmdError:
            return False

        return name in pools

    def pool_state(self, name):
        """
        Get pool's state.

        :return: active/inactive, and None when something wrong.
        """
        try:
            pools = self.list_pools()
        except error.CmdError:
            return None

        if self.pool_exists(name):
            details_dict = pools[name]
            try:
                return details_dict['State']
            except KeyError:
                pass
        return None

    def pool_info(self, name):
        """
        Get pool's information.

        :return: A dict include pool's information:
                Name ==> value
                UUID ==> value
                ...
        """
        info = {}
        try:
            result = self.virsh_instance.pool_info(name, ignore_status=False)
        except error.CmdError:
            return info

        for line in result.stdout.splitlines():
            params = line.split(':')
            if len(params) == 2:
                name = params[0].strip()
                value = params[1].strip()
                info[name] = value
        return info

    def get_pool_uuid(self, name):
        """
        Get pool's uuid.

        :return: Pool uuid.
        """
        return self.pool_info(name)["UUID"]

    def is_pool_active(self, name):
        """
        Check whether pool is active on given libvirt
        """
        if self.pool_state(name) == "active":
            return True
        return False

    def is_pool_persistent(self, name):
        """
        Check whether pool is persistent
        """
        if self.pool_info(name)["Persistent"] == "yes":
            return True
        return False

    def delete_pool(self, name):
        """
        Destroy and Delete a pool if it exists on given libvirt
        """
        if self.is_pool_active(name):
            if not self.virsh_instance.pool_destroy(name):
                # TODO: Allow pool_destroy to raise exception.
                #       Because some testcase rely on this function,
                #       I should start this work after this module is accepted.
                logging.error("Destroy pool '%s' failed.", name)
                return False

        if self.pool_exists(name):
            try:
                self.virsh_instance.pool_undefine(name, ignore_status=False)
            except error.CmdError:
                logging.error("Undefine pool '%s' failed.", name)
                return False
        logging.info("Deleted pool '%s'", name)
        return True

    def set_pool_autostart(self, name):
        """
        Set given pool as autostart
        """
        try:
            self.virsh_instance.pool_autostart(name, ignore_status=False)
        except error.CmdError:
            logging.error("Autostart pool '%s' failed.", name)
            return False
        logging.info("Set pool '%s' autostart.", name)
        return True

    def build_pool(self, name):
        """
        Build pool.
        """
        try:
            self.virsh_instance.pool_build(name, ignore_status=False)
        except error.CmdError:
            logging.error("Build pool '%s' failed.", name)
            return False
        logging.info("Built pool '%s'", name)
        return True

    def start_pool(self, name):
        """
        Start pool if it is inactive.
        """
        if self.is_pool_active(name):
            logging.info("Pool '%s' is already active.", name)
            return True
        try:
            self.virsh_instance.pool_start(name, ignore_status=False)
        except error.CmdError:
            logging.error("Start pool '%s' failed.", name)
            return False
        logging.info("Started pool '%s'", name)
        return True

    def destroy_pool(self, name):
        """
        Destroy pool if it is active.
        """
        if not self.is_pool_active(name):
            logging.info("pool '%s' is already inactive.", name)
            return True
        return self.virsh_instance.pool_destroy(name)

    def define_dir_pool(self, name, target_path):
        """
        Define a directory type pool.
        """
        try:
            self.virsh_instance.pool_define_as(name, "dir", target_path,
                                               ignore_status=False)
        except error.CmdError:
            logging.error("Define dir pool '%s' failed.", name)
            return False
        logging.info("Defined pool '%s'", name)
        return True

    def define_fs_pool(self, name, block_device, target_path):
        """
        Define a filesystem type pool.
        """
        try:
            self.virsh_instance.pool_define_as(name, "fs", target_path,
                                               extra="--source-dev %s" % block_device,
                                               ignore_status=False)
        except error.CmdError:
            logging.error("Define fs pool '%s' failed.", name)
            return False
        logging.info("Defined pool '%s'", name)
        return True

    def define_lvm_pool(self, name, block_device, vg_name, target_path):
        """
        Define a lvm type pool.
        """
        try:
            extra = "--source-dev %s --source-name %s" % (block_device,
                                                          vg_name)
            self.virsh_instance.pool_define_as(name, "logical", target_path,
                                               extra, ignore_status=False)
        except error.CmdError:
            logging.error("Define logic pool '%s' failed.", name)
            return False
        logging.info("Defined pool '%s'", name)
        return True

    def define_disk_pool(self, name, block_device, target_path):
        """
        Define a disk type pool.
        """
        try:
            extra = "--source-dev %s" % block_device
            self.virsh_instance.pool_define_as(name, "disk", target_path,
                                               extra, ignore_status=False)
        except error.CmdError:
            logging.error("Define disk pool '%s' failed.", name)
            return False
        logging.info("Defined pool '%s'", name)
        return True

    def define_iscsi_pool(self, name, source_host, source_dev, target_path):
        """
        Define a iscsi type pool.
        """
        try:
            extra = "--source-host %s  --source-dev %s" % (source_host,
                                                           source_dev)
            self.virsh_instance.pool_define_as(name, "iscsi", target_path,
                                               extra, ignore_status=False)
        except error.CmdError:
            logging.error("Define iscsi pool '%s' failed.", name)
            return False
        logging.info("Define pool '%s'", name)
        return True

    def define_netfs_pool(self, name, source_host, source_path, target_path):
        """
        Define a netfs type pool.
        """
        try:
            extra = "--source-host %s --source-path %s" % (source_host,
                                                           target_path)
            self.virsh_instance.pool_define_as(name, "netfs", target_path,
                                               extra, ignore_status=False)
        except error.CmdError:
            logging.error("Define netfs pool '%s' failed.", name)
            return False
        logging.info("Define pool '%s'", name)
        return True


class PoolVolume(object):

    """Volume Manager for libvirt storage pool."""

    def __init__(self, pool_name, virsh_instance=virsh):
        self.pool_name = pool_name
        self.virsh_instance = virsh_instance

    def list_volumes(self):
        """
        Return a dict include volumes' name(key) and path(value).
        """
        result = self.virsh_instance.vol_list(self.pool_name,
                                              ignore_status=False)
        volumes = {}
        lines = result.stdout.strip().splitlines()
        if len(lines) > 2:
            head = lines[0]
            lines = lines[2:]
        else:
            return volumes

        for line in lines:
            # Path may be not standard unix path
            try:
                path = re.findall("\s+/.*", line)[0]
            except IndexError:
                # Do not find a path
                path = ""
            name = line.split(path)[0].lstrip()
            volumes[name] = path.strip()
        return volumes

    def volume_exists(self, name):
        try:
            volumes = self.list_volumes()
        except error.CmdError:
            return False
        return name in volumes

    def volume_info(self, name):
        """
        Get volume's information with command vol-info.
        """
        info = {}
        try:
            result = self.virsh_instance.vol_info(name, self.pool_name,
                                                  ignore_status=False)
        except error.CmdError, detail:
            logging.error("Get volume information failed:%s", detail)
            return info

        for line in result.stdout.strip().splitlines():
            attr = line.split(':')[0]
            value = line.split("%s:" % attr)[-1].strip()
            info[attr] = value
        return info

    def create_volume(self, name, capability,
                      allocation=None, frmt=None):
        """
        Create a volume in pool.
        """
        if self.volume_exists(name):
            logging.debug("Volume '%s' already exists.", name)
            return False
        try:
            self.virsh_instance.vol_create_as(name, self.pool_name,
                                              capability, allocation, frmt,
                                              ignore_status=False, debug=True)
        except error.CmdError, detail:
            logging.error("Create volume failed:%s", detail)
            return False

        if not self.volume_exists(name):
            logging.error("Created volume does not exist:%s",
                          self.list_volumes())
            return False
        return True

    def delete_volume(self, name):
        """
        Remove a volume.
        """
        if self.volume_exists(name):
            try:
                self.virsh_instance.vol_delete(name, self.pool_name,
                                               ignore_status=False)
            except error.CmdError, detail:
                logging.error("Delete volume failed:%s", detail)
                return False
            if not self.volume_exists(name):
                logging.debug("Volume '%s' has been deleted.", name)
                return True
            else:
                logging.debug("Delete volume '%s' failed.", name)
                return False
        else:
            logging.info("Volume '%s' does not exist.", name)
            return True     # Return True for expected result

    def clone_volume(self, old_name, new_name):
        """
        Clone a volume
        """
        if self.volume_exists(old_name) and not self.volume_exists(new_name):
            try:
                self.virsh_instance.vol_clone(old_name, new_name,
                                              self.pool_name,
                                              ignore_status=False)
            except error.CmdError, detail:
                logging.error("Clone volume failed:%s", detail)
                return False
            if self.volume_exists(new_name):
                logging.debug("Volume '%s' has been created by clone.",
                              new_name)
                return True
            else:
                logging.debug("Volume '%s' clone failed.", old_name)
                return False
        else:
            logging.info("Volume '%s' does not exist or '%s' has been exist."
                         % (old_name, new_name))
            return False
