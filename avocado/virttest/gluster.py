"""
GlusterFS Support
This file has the functions that helps
* To create/check gluster volume.
* To start/check gluster services.
* To create gluster uri which can be used as disk image file path.
"""

import logging
import os
import re
import shutil
from autotest.client.shared import utils, error
import data_dir
import utils_misc
import utils_net
import socket


class GlusterError(Exception):
    pass


class GlusterBrickError(GlusterError):

    def __init__(self, error_mgs):
        super(GlusterBrickError, self).__init__(error_mgs)
        self.error_mgs = error_mgs

    def __str__(self):
        return ("Gluster: %s" % (self.error_mgs))


@error.context_aware
def glusterd_start():
    """
    Check for glusterd status
    """
    cmd = "service glusterd status"
    output = utils.system_output(cmd, ignore_status=True)
    if 'inactive' or 'stopped' in output:
        cmd = "service glusterd start"
        error.context("Starting gluster dameon failed")
        output = utils.system_output(cmd)


@error.context_aware
def is_gluster_vol_started(vol_name):
    """
    Returns if the volume is started, if not send false
    """
    cmd = "gluster volume info %s" % vol_name
    error.context("Gluster volume info failed for volume: %s" % vol_name)
    vol_info = utils.system_output(cmd)
    volume_status = re.findall(r'Status: (\S+)', vol_info)
    if 'Started' in volume_status:
        return True
    else:
        return False


@error.context_aware
def gluster_vol_start(vol_name):
    """
    Starts the volume if it is stopped
    """
    # Check if the volume is stopped, if then start
    if not is_gluster_vol_started(vol_name):
        error.context("Gluster volume start failed for volume; %s" % vol_name)
        cmd = "gluster volume start %s" % vol_name
        utils.system(cmd)
        return True
    else:
        return True


@error.context_aware
def gluster_vol_stop(vol_name, force=False):
    """
    Starts the volume if it is stopped
    """
    # Check if the volume is stopped, if then start
    if is_gluster_vol_started(vol_name):
        error.context("Gluster volume stop for volume; %s" % vol_name)
        if force:
            cmd = "gluster volume stop %s force" % vol_name
        else:
            cmd = "gluster volume stop %s" % vol_name
        utils.run(cmd, ignore_status=False,
                  stdout_tee=utils.TEE_TO_LOGS,
                  stderr_tee=utils.TEE_TO_LOGS,
                  stdin="y\n",
                  verbose=True)
        return True
    else:
        return True


@error.context_aware
def gluster_vol_delete(vol_name):
    """
    Starts the volume if it is stopped
    """
    # Check if the volume is stopped, if then start
    if not is_gluster_vol_started(vol_name):
        error.context("Gluster volume delete; %s" % vol_name)
        cmd = "gluster volume delete %s" % vol_name
        utils.run(cmd, ignore_status=False,
                  stdout_tee=utils.TEE_TO_LOGS,
                  stderr_tee=utils.TEE_TO_LOGS,
                  stdin="y\n",
                  verbose=True)
        return True
    else:
        return False


@error.context_aware
def is_gluster_vol_avail(vol_name):
    """
    Returns if the volume already available
    """
    cmd = "gluster volume info"
    error.context("Gluster volume info failed")
    output = utils.system_output(cmd)
    volume_name = re.findall(r'Volume Name: (%s)\n' % vol_name, output)
    if volume_name:
        return gluster_vol_start(vol_name)


def gluster_brick_create(brick_path, force=False):
    """
    Creates brick
    """
    if os.path.isdir(brick_path) and force:
        gluster_brick_delete(brick_path)
    try:
        os.mkdir(brick_path)
        return True
    except OSError, details:
        logging.error("Not able to create brick folder %s", details)


def gluster_brick_delete(brick_path):
    """
    Creates brick
    """
    if os.path.isdir(brick_path):
        try:
            shutil.rmtree(brick_path)
            return True
        except OSError, details:
            logging.error("Not able to create brick folder %s", details)


@error.context_aware
def gluster_vol_create(vol_name, hostname, brick_path, force=False):
    """
    Gluster Volume Creation
    """
    # Create a brick
    if is_gluster_vol_avail(vol_name):
        gluster_vol_stop(vol_name, True)
        gluster_vol_delete(vol_name)
        gluster_brick_delete(brick_path)

    gluster_brick_create(brick_path)

    cmd = "gluster volume create %s %s:/%s" % (vol_name, hostname,
                                               brick_path)
    error.context("Volume creation failed")
    utils.system(cmd)
    return is_gluster_vol_avail(vol_name)


def glusterfs_mount(g_uri, mount_point):
    """
    Mount gluster volume to mountpoint.

    :param g_uri: stripped gluster uri from create_gluster_uri(.., True)
    :type g_uri: str
    """
    utils_misc.mount(g_uri, mount_point, "glusterfs", None,
                     False, "fuse.glusterfs")


@error.context_aware
def create_gluster_vol(params):
    vol_name = params.get("gluster_volume_name")
    force = params.get('force_recreate_gluster') == "yes"

    brick_path = params.get("gluster_brick")
    if not os.path.isabs(brick_path):  # do nothing when path is absolute
        base_dir = params.get("images_base_dir", data_dir.get_data_dir())
        brick_path = os.path.join(base_dir, brick_path)

    error.context("Host name lookup failed")
    hostname = socket.gethostname()
    if not hostname or hostname == "(none)":
        if_up = utils_net.get_net_if(state="UP")
        for i in if_up:
            ipv4_value = utils_net.get_net_if_addrs(i)["ipv4"]
            logging.debug("ipv4_value is %s", ipv4_value)
            if ipv4_value != []:
                ip_addr = ipv4_value[0]
                break
        hostname = ip_addr

    # Start the gluster dameon, if not started
    glusterd_start()
    # Check for the volume is already present, if not create one.
    if not is_gluster_vol_avail(vol_name) or force:
        return gluster_vol_create(vol_name, hostname, brick_path, force)
    else:
        return True


@error.context_aware
def create_gluster_uri(params, stripped=False):
    """
    Find/create gluster volume
    """
    vol_name = params.get("gluster_volume_name")

    error.context("Host name lookup failed")
    hostname = socket.gethostname()
    gluster_server = params.get("gluster_server")
    gluster_port = params.get("gluster_port", "0")
    if not gluster_server:
        gluster_server = hostname
    if not gluster_server or gluster_server == "(none)":
        if_up = utils_net.get_net_if(state="UP")
        ip_addr = utils_net.get_net_if_addrs(if_up[0])["ipv4"][0]
        gluster_server = ip_addr

    # Start the gluster dameon, if not started
    # Building gluster uri
    gluster_uri = None
    if stripped:
        gluster_uri = "%s:/%s" % (gluster_server, vol_name)
    else:
        gluster_uri = "gluster://%s:%s/%s/" % (gluster_server, gluster_port,
                                               vol_name)
    return gluster_uri


def file_exists(params, filename_path):
    sg_uri = create_gluster_uri(params, stripped=True)
    g_uri = create_gluster_uri(params, stripped=False)
    # Using directly /tmp dir because directory should be really temporary and
    # should be deleted immediately when no longer needed and
    # created directory don't file tmp dir by any data.
    tmpdir = "gmount-%s" % (utils_misc.generate_random_string(6))
    tmpdir_path = os.path.join("/tmp", tmpdir)
    while os.path.exists(tmpdir_path):
        tmpdir = "gmount-%s" % (utils_misc.generate_random_string(6))
        tmpdir_path = os.path.join("/tmp", tmpdir)
    ret = False
    try:
        try:
            os.mkdir(tmpdir_path)
            glusterfs_mount(sg_uri, tmpdir_path)
            mount_filename_path = os.path.join(tmpdir_path,
                                               filename_path[len(g_uri):])
            if os.path.exists(mount_filename_path):
                ret = True
        except Exception, e:
            logging.error("Failed to mount gluster volume %s to"
                          " mount dir %s: %s" % (sg_uri, tmpdir_path, e))
    finally:
        if utils_misc.umount(sg_uri, tmpdir_path, "glusterfs", False,
                             "fuse.glusterfs"):
            try:
                os.rmdir(tmpdir_path)
            except OSError:
                pass
        else:
            logging.warning("Unable to unmount tmp directory %s with glusterfs"
                            " mount.", tmpdir_path)
    return ret


def get_image_filename(params, image_name, image_format):
    """
    Form the image file name using gluster uri
    """

    img_name = image_name.split('/')[-1]
    gluster_uri = create_gluster_uri(params)
    image_filename = "%s%s.%s" % (gluster_uri, img_name, image_format)
    return image_filename
