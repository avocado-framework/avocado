"""
Classes and functions to handle block/disk images for KVM.

This exports:
  - two functions for get image/blkdebug filename
  - class for image operates and basic parameters
"""
import logging
import os
import re
from autotest.client.shared import error
from autotest.client import utils
import utils_misc
import virt_vm
import storage
import data_dir


class QemuImg(storage.QemuImg):

    """
    KVM class for handling operations of disk/block images.
    """

    def __init__(self, params, root_dir, tag):
        """
        Init the default value for image object.

        :param params: Dictionary containing the test parameters.
        :param root_dir: Base directory for relative filenames.
        :param tag: Image tag defined in parameter images
        """
        storage.QemuImg.__init__(self, params, root_dir, tag)
        self.image_cmd = utils_misc.get_qemu_img_binary(params)
        q_result = utils.run(self.image_cmd, ignore_status=True,
                             verbose=False)
        self.help_text = q_result.stdout

    @error.context_aware
    def create(self, params, ignore_errors=False):
        """
        Create an image using qemu_img or dd.

        :param params: Dictionary containing the test parameters.
        :param ignore_errors: Whether to ignore errors on the image creation
                              cmd.

        :note: params should contain:

               image_name
                   name of the image file, without extension
               image_format
                   format of the image (qcow2, raw etc)
               image_cluster_size (optional)
                   cluster size for the image
               image_size
                   requested size of the image (a string qemu-img can
                   understand, such as '10G')
               create_with_dd
                   use dd to create the image (raw format only)
               base_image(optional)
                   the base image name when create snapshot
               base_format(optional)
                   the format of base image
               encrypted(optional)
                   if the image is encrypted, allowed values: on and off.
                   Default is "off"
               preallocated(optional)
                   if preallocation when create image, allowed values: off,
                   metadata. Default is "off"

        :return: tuple (path to the image created, utils.CmdResult object
                 containing the result of the creation command).
        """
        if params.get("create_with_dd") == "yes" and self.image_format == "raw":
            # maps K,M,G,T => (count, bs)
            human = {'K': (1, 1),
                     'M': (1, 1024),
                     'G': (1024, 1024),
                     'T': (1024, 1048576),
                     }
            if human.has_key(self.size[-1]):
                block_size = human[self.size[-1]][1]
                size = int(self.size[:-1]) * human[self.size[-1]][0]
            qemu_img_cmd = ("dd if=/dev/zero of=%s count=%s bs=%sK"
                            % (self.image_filename, size, block_size))
        else:
            qemu_img_cmd = self.image_cmd
            qemu_img_cmd += " create"

            qemu_img_cmd += " -f %s" % self.image_format

            image_cluster_size = params.get("image_cluster_size", None)
            preallocated = params.get("preallocated", "off")
            encrypted = params.get("encrypted", "off")
            image_extra_params = params.get("image_extra_params", "")
            has_backing_file = params.get('has_backing_file')

            qemu_img_cmd += " -o "
            if preallocated != "off":
                qemu_img_cmd += "preallocation=%s," % preallocated

            if encrypted != "off":
                qemu_img_cmd += "encrypted=%s," % encrypted

            if image_cluster_size is not None:
                qemu_img_cmd += "cluster_size=%s," % image_cluster_size

            if has_backing_file == "yes":
                backing_param = params.object_params("backing_file")
                backing_file = storage.get_image_filename(backing_param,
                                                          self.root_dir)
                backing_fmt = backing_param.get("image_format")
                qemu_img_cmd += "backing_file=%s," % backing_file

                qemu_img_cmd += "backing_fmt=%s," % backing_fmt

            if image_extra_params:
                qemu_img_cmd += "%s," % image_extra_params
            qemu_img_cmd = qemu_img_cmd.rstrip(" -o")
            qemu_img_cmd = qemu_img_cmd.rstrip(",")

            if self.base_tag:
                qemu_img_cmd += " -b %s" % self.base_image_filename
                if self.base_format:
                    qemu_img_cmd += " -F %s" % self.base_format

            qemu_img_cmd += " %s" % self.image_filename

            qemu_img_cmd += " %s" % self.size

        if (params.get("image_backend", "filesystem") == "filesystem"):
            image_dirname = os.path.dirname(self.image_filename)
            if image_dirname and not os.path.isdir(image_dirname):
                e_msg = ("Parent directory of the image file %s does "
                         "not exist" % self.image_filename)
                logging.error(e_msg)
                logging.error("This usually means a serious setup error.")
                logging.error("Please verify if your data dir contains the "
                              "expected directory structure")
                logging.error("Backing data dir: %s",
                              data_dir.get_backing_data_dir())
                logging.error("Directory structure:")
                for root, _, _ in os.walk(data_dir.get_backing_data_dir()):
                    logging.error(root)

                logging.warning("We'll try to proceed by creating the dir. "
                                "Other errors may ensue")
                os.makedirs(image_dirname)

        msg = "Create image by command: %s" % qemu_img_cmd
        error.context(msg, logging.info)
        cmd_result = utils.run(qemu_img_cmd, verbose=False, ignore_status=True)
        if cmd_result.exit_status != 0 and not ignore_errors:
            raise error.TestError("Failed to create image %s" %
                                  self.image_filename)

        return self.image_filename, cmd_result

    def convert(self, params, root_dir, cache_mode=None):
        """
        Convert image

        :param params: dictionary containing the test parameters
        :param root_dir: dir for save the convert image
        :param cache_mode: The cache mode used to write the output disk image.
                           Valid options are: ``none``, ``writeback``
                           (default), ``writethrough``, ``directsync`` and
                           ``unsafe``.

        :note: params should contain:

            convert_image_tag
                the image name of the convert image
            convert_filename
                the name of the image after convert
            convert_fmt
                the format after convert
            compressed
                indicates that target image must be compressed
            encrypted
                there are two value "off" and "on", default value is "off"
        """
        convert_image_tag = params["image_convert"]
        convert_image = params["convert_name_%s" % convert_image_tag]
        convert_compressed = params.get("convert_compressed")
        convert_encrypted = params.get("convert_encrypted", "off")
        convert_format = params["convert_format_%s" % convert_image_tag]
        params_convert = {"image_name": convert_image,
                          "image_format": convert_format}

        convert_image_filename = storage.get_image_filename(params_convert,
                                                            root_dir)

        cmd = self.image_cmd
        cmd += " convert"
        if convert_compressed == "yes":
            cmd += " -c"
        if convert_encrypted != "off":
            cmd += " -o encryption=%s" % convert_encrypted
        if self.image_format:
            cmd += " -f %s" % self.image_format
        cmd += " -O %s" % convert_format
        if cache_mode:
            cmd += " -t %s" % cache_mode
        cmd += " %s %s" % (self.image_filename, convert_image_filename)

        logging.info("Convert image %s from %s to %s", self.image_filename,
                     self.image_format, convert_format)

        utils.system(cmd)

        return convert_image_tag

    def rebase(self, params, cache_mode=None):
        """
        Rebase image.

        :param params: dictionary containing the test parameters
        :param cache_mode: the cache mode used to write the output disk image,
                           the valid options are: 'none', 'writeback' (default),
                           'writethrough', 'directsync' and 'unsafe'.

        :note: params should contain:

            cmd
                qemu-img cmd
            snapshot_img
                the snapshot name
            base_img
                base image name
            base_fmt
                base image format
            snapshot_fmt
                the snapshot format
            mode
                there are two value, "safe" and "unsafe", default is "safe"
        """
        self.check_option("base_image_filename")
        self.check_option("base_format")

        rebase_mode = params.get("rebase_mode")
        cmd = self.image_cmd
        cmd += " rebase"
        if self.image_format:
            cmd += " -f %s" % self.image_format
        if cache_mode:
            cmd += " -t %s" % cache_mode
        if rebase_mode == "unsafe":
            cmd += " -u"
        if self.base_tag:
            cmd += " -b %s -F %s %s" % (self.base_image_filename,
                                        self.base_format, self.image_filename)
        else:
            raise error.TestError("Can not find the image parameters need"
                                  " for rebase.")

        logging.info("Rebase snapshot %s to %s..." % (self.image_filename,
                                                      self.base_image_filename))
        utils.system(cmd)

        return self.base_tag

    def commit(self, params={}, cache_mode=None):
        """
        Commit image to it's base file

        :param cache_mode: the cache mode used to write the output disk image,
            the valid options are: 'none', 'writeback' (default),
            'writethrough', 'directsync' and 'unsafe'.
        """
        cmd = self.image_cmd
        cmd += " commit"
        if cache_mode:
            cmd += " -t %s" % cache_mode
        cmd += " -f %s %s" % (self.image_format, self.image_filename)
        logging.info("Commit snapshot %s" % self.image_filename)
        utils.system(cmd)

        return self.image_filename

    def snapshot_create(self):
        """
        Create a snapshot image.

        :note: params should contain:
               snapshot_image_name -- the name of snapshot image file
        """

        cmd = self.image_cmd
        if self.snapshot_tag:
            cmd += " snapshot -c %s" % self.snapshot_image_filename
        else:
            raise error.TestError("Can not find the snapshot image"
                                  " parameters")
        cmd += " %s" % self.image_filename

        utils.system_output(cmd)

        return self.snapshot_tag

    def snapshot_del(self, blkdebug_cfg=""):
        """
        Delete a snapshot image.

        :param blkdebug_cfg: The configure file of blkdebug

        :note: params should contain:
               snapshot_image_name -- the name of snapshot image file
        """

        cmd = self.image_cmd
        if self.snapshot_tag:
            cmd += " snapshot -d %s" % self.snapshot_image_filename
        else:
            raise error.TestError("Can not find the snapshot image"
                                  " parameters")
        if blkdebug_cfg:
            cmd += " blkdebug:%s:%s" % (blkdebug_cfg, self.image_filename)
        else:
            cmd += " %s" % self.image_filename

        utils.system_output(cmd)

    def snapshot_list(self):
        """
        List all snapshots in the given image
        """
        cmd = self.image_cmd
        cmd += " snapshot -l %s" % self.image_filename

        return utils.system_output(cmd)

    def remove(self):
        """
        Remove an image file.
        """
        logging.debug("Removing image file %s", self.image_filename)
        if os.path.exists(self.image_filename):
            os.unlink(self.image_filename)
        else:
            logging.debug("Image file %s not found", self.image_filename)

    def info(self):
        """
        Run qemu-img info command on image file and return its output.
        """
        logging.debug("Run qemu-img info comamnd on %s", self.image_filename)
        cmd = self.image_cmd
        if os.path.exists(self.image_filename):
            cmd += " info %s" % self.image_filename
            output = utils.system_output(cmd)
        else:
            logging.debug("Image file %s not found", self.image_filename)
            output = None
        return output

    def get_format(self):
        """
        Get the fimage file format.
        """
        image_info = self.info()
        if image_info:
            image_format = re.findall("file format: (\w+)", image_info)[0]
        else:
            image_format = None
        return image_format

    def support_cmd(self, cmd):
        """
        Verifies whether qemu-img supports command cmd.

        :param cmd: Command string.
        """
        supports_cmd = True

        if cmd not in self.help_text:
            logging.error("%s does not support command '%s'", self.image_cmd,
                          cmd)
            supports_cmd = False

        return supports_cmd

    def compare_images(self, image1, image2, verbose=True):
        """
        Compare 2 images using the appropriate tools for each virt backend.

        :param image1: image path of first image
        :param image2: image path of second image
        :param verbose: Record output in debug file or not
        """
        compare_images = self.support_cmd("compare")
        if not compare_images:
            logging.debug("Skipping image comparison "
                          "(lack of support in qemu-img)")
        else:
            logging.info("Comparing images %s and %s", image1, image2)
            compare_cmd = "%s compare %s %s" % (self.image_cmd, image1, image2)
            rv = utils.run(compare_cmd, ignore_status=True)

            if verbose:
                logging.debug("Output from command: %s" % rv.stdout)

            if rv.exit_status == 0:
                logging.info("Compared images are equal")
            elif rv.exit_status == 1:
                raise error.TestFail("Compared images differ")
            else:
                raise error.TestError("Error in image comparison")

    def check_image(self, params, root_dir):
        """
        Check an image using the appropriate tools for each virt backend.

        :param params: Dictionary containing the test parameters.
        :param root_dir: Base directory for relative filenames.

        :note: params should contain:
               image_name -- the name of the image file, without extension
               image_format -- the format of the image (qcow2, raw etc)

        :raise VMImageCheckError: In case qemu-img check fails on the image.
        """
        image_filename = self.image_filename
        logging.debug("Checking image file %s", image_filename)
        qemu_img_cmd = self.image_cmd
        image_is_checkable = self.image_format in ['qcow2', 'qed']

        if (storage.file_exists(params, image_filename) or
                params.get("enable_gluster", "no") == "yes") and image_is_checkable:
            check_img = self.support_cmd("check") and self.support_cmd("info")
            if not check_img:
                logging.debug("Skipping image check "
                              "(lack of support in qemu-img)")
            else:
                try:
                    utils.run("%s info %s" % (qemu_img_cmd, image_filename),
                              verbose=True)
                except error.CmdError:
                    logging.error("Error getting info from image %s",
                                  image_filename)

                cmd_result = utils.run("%s check %s" %
                                       (qemu_img_cmd, image_filename),
                                       ignore_status=True, verbose=True)
                # Error check, large chances of a non-fatal problem.
                # There are chances that bad data was skipped though
                if cmd_result.exit_status == 1:
                    for e_line in cmd_result.stdout.splitlines():
                        logging.error("[stdout] %s", e_line)
                    for e_line in cmd_result.stderr.splitlines():
                        logging.error("[stderr] %s", e_line)
                    chk = params.get("backup_image_on_check_error", "no")
                    if chk == "yes":
                        self.backup_image(params, root_dir, "backup", False)
                    raise error.TestWarn("qemu-img check error. Some bad "
                                         "data in the image may have gone"
                                         " unnoticed (%s)" % image_filename)
                # Exit status 2 is data corruption for sure,
                # so fail the test
                elif cmd_result.exit_status == 2:
                    for e_line in cmd_result.stdout.splitlines():
                        logging.error("[stdout] %s", e_line)
                    for e_line in cmd_result.stderr.splitlines():
                        logging.error("[stderr] %s", e_line)
                    chk = params.get("backup_image_on_check_error", "no")
                    if chk == "yes":
                        self.backup_image(params, root_dir, "backup", False)
                    raise virt_vm.VMImageCheckError(image_filename)
                # Leaked clusters, they are known to be harmless to data
                # integrity
                elif cmd_result.exit_status == 3:
                    raise error.TestWarn("Leaked clusters were noticed"
                                         " during image check. No data "
                                         "integrity problem was found "
                                         "though. (%s)" % image_filename)

                # Just handle normal operation
                if params.get("backup_image", "no") == "yes":
                    self.backup_image(params, root_dir, "backup", True, True)
        else:
            if not storage.file_exists(params, image_filename):
                logging.debug("Image file %s not found, skipping check",
                              image_filename)
            elif not image_is_checkable:
                logging.debug(
                    "Image format %s is not checkable, skipping check",
                    self.image_format)


class Iscsidev(storage.Iscsidev):

    """
    Class for handle iscsi devices for VM
    """

    def __init__(self, params, root_dir, tag):
        """
        Init the default value for image object.

        :param params: Dictionary containing the test parameters.
        :param root_dir: Base directory for relative filenames.
        :param tag: Image tag defined in parameter images
        """
        super(Iscsidev, self).__init__(params, root_dir, tag)

    def setup(self):
        """
        Access the iscsi target. And return the local raw device name.
        """
        if self.iscsidevice.logged_in():
            logging.warn("Session already present. Don't need to"
                         " login again")
        else:
            self.iscsidevice.login()

        if utils_misc.wait_for(self.iscsidevice.get_device_name,
                               self.iscsi_init_timeout):
            device_name = self.iscsidevice.get_device_name()
        else:
            raise error.TestError("Can not get iscsi device name in host"
                                  " in %ss" % self.iscsi_init_timeout)

        if self.device_id:
            device_name += self.device_id
        return device_name

    def cleanup(self):
        """
        Logout the iscsi target and clean up the config and image.
        """
        if self.exec_cleanup:
            self.iscsidevice.cleanup()
            if self.emulated_file_remove:
                logging.debug("Removing file %s", self.emulated_image)
                if os.path.exists(self.emulated_image):
                    os.unlink(self.emulated_image)
                else:
                    logging.debug("File %s not found", self.emulated_image)


class LVMdev(storage.LVMdev):

    """
    Class for handle lvm devices for VM
    """

    def __init__(self, params, root_dir, tag):
        """
        Init the default value for image object.

        :param params: Dictionary containing the test parameters.
        :param root_dir: Base directory for relative filenames.
        :param tag: Image tag defined in parameter images
        """
        super(LVMdev, self).__init__(params, root_dir, tag)

    def setup(self):
        """
        Get logical volume path;
        """
        return self.lvmdevice.setup()

    def cleanup(self):
        """
        Cleanup useless volumes;
        """
        return self.lvmdevice.cleanup()
