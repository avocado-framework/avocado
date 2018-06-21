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
# Copyright: 2016 IBM
# Author: Narasimhan V <sim@linux.vnet.ibm.com>

"""
Module with multipath related utility functions.
It needs root access.
"""

import time
import logging
import ast
from . import distro
from . import process
from . import service
from . import wait


def get_svc_name():
    """
    Gets the multipath service name based on distro.
    """
    if distro.detect().name == 'Ubuntu':
        return "multipath-tools"
    return "multipathd"


def form_conf_mpath_file(blacklist="", defaults_extra=""):
    """
    Form a multipath configuration file, and restart multipath service.

    :param blacklist: Entry in conf file to indicate blacklist section.
    :param defaults_extra: Extra entry in conf file in defaults section.
    """
    conf_file = "/etc/multipath.conf"
    with open(conf_file, "w") as mpath_fp:
        mpath_fp.write("defaults {\n")
        mpath_fp.write("    find_multipaths yes\n")
        mpath_fp.write("    user_friendly_names yes\n")
        if defaults_extra:
            mpath_fp.write("    %s\n" % defaults_extra)
        mpath_fp.write("}\n")
        if blacklist:
            mpath_fp.write("blacklist {\n")
            mpath_fp.write("    %s\n" % blacklist)
            mpath_fp.write("}\n")
    logging.debug(open(conf_file, "r").read())
    # The reason for sleep here is to give some time for change in
    # multipath.conf file to take effect.
    time.sleep(5)
    mpath_svc = service.SpecificServiceManager(get_svc_name())
    mpath_svc.restart()
    wait.wait_for(mpath_svc.status, timeout=10)


def device_exists(path):
    """
    Checks if a given path exists.

    :return: True if path exists, False if does not exist.
    """
    cmd = "multipath -l %s" % path
    if process.system(cmd, ignore_status=True, sudo=True) != 0:
        return False
    return True


def get_mpath_name(wwid):
    """
    Get multipath name for a given wwid.

    :param wwid: wwid of multipath device.

    :return: Name of multipath device.
    """
    if device_exists(wwid):
        cmd = "multipath -l %s" % wwid
        return process.system_output(cmd, sudo=True).split()[0]


def get_multipath_wwids():
    """
    Get list of multipath wwids.

    :return: List of multipath wwids.
    """
    cmd = "egrep -v '^($|#)' /etc/multipath/wwids"
    wwids = process.system_output(cmd, ignore_status=True, sudo=True)
    wwids = wwids.strip("\n").replace("/", "").split("\n")
    return wwids


def get_paths(wwid):
    """
    Get list of paths, given a multipath wwid.

    :return: List of paths.
    """
    if not device_exists(wwid):
        return
    cmd = "multipath -ll %s" % wwid
    lines = process.system_output(cmd, sudo=True).strip("\n")
    paths = []
    for line in lines.split("\n"):
        if not (('size' in line) or ('policy' in line) or (wwid in line)):
            paths.append(line.split()[-5])
    return paths


def get_multipath_details():
    """
    Get multipath details as a dictionary, as given by the command:
    multipathd show maps json

    :return: Dictionary of multipath output in json format.
    """
    mpath_op = process.system_output("multipathd show maps json", sudo=True)
    if 'multipath-tools v' in mpath_op:
        return ''
    mpath_op = ast.literal_eval(mpath_op.replace("\n", '').replace(' ', ''))
    return mpath_op


def is_path_a_multipath(disk_path):
    """
    Check if given disk path is part of a multipath.

    :param disk_path: disk path. Example: sda, sdb.

    :return: True if part of multipath, else False.
    """
    if not process.system("multipath -c /dev/%s" % disk_path, sudo=True,
                          ignore_status=True):
        return True
    return False


def get_path_status(disk_path):
    """
    Return the status of a path in multipath.

    :param disk_path: disk path. Example: sda, sdb.

    :return: Tuple in the format of (dm status, dev status, checker status)
    """
    mpath_op = get_multipath_details()
    if not mpath_op:
        return ('', '', '')
    for maps in mpath_op['maps']:
        for path_groups in maps['path_groups']:
            for paths in path_groups['paths']:
                if paths['dev'] == disk_path:
                    return(paths['dm_st'], paths['dev_st'], paths['chk_st'])


def fail_path(path):
    """
    failing the individual paths
    :param disk_path: disk path. Example: sda, sdb.
    :return: True or False
    """
    def is_failed():
        path_stat = get_path_status(path)
        if path_stat[0] == 'failed' and path_stat[2] == 'faulty':
            return True
        return False

    cmd = 'multipathd -k"fail path %s"' % path
    if process.system(cmd) == 0:
        return wait.wait_for(is_failed, timeout=10) or False


def reinstate_path(path):
    """
    reinstating the individual paths
    :param disk_path: disk path. Example: sda, sdb.
    :return: True or False
    """
    def is_reinstated():
        path_stat = get_path_status(path)
        if path_stat[0] == 'active' and path_stat[2] == 'ready':
            return True
        return False
    cmd = 'multipathd -k"reinstate path %s"' % path
    if process.system(cmd) == 0:
        return wait.wait_for(is_reinstated, timeout=10) or False


def get_policy(wwid):
    """
    Gets path_checker policy, given a multipath wwid.

    :return: path checker policy.
    """
    if device_exists(wwid):
        cmd = "multipath -ll %s" % wwid
        lines = process.system_output(cmd, sudo=True).strip("\n")
        for line in lines.split("\n"):
            if 'policy' in line:
                return line.split("'")[1].split()[0]


def get_size(wwid):
    """
    Gets size of device, given a multipath wwid.

    :return: size of multipath device.
    """
    if device_exists(wwid):
        cmd = "multipath -ll %s" % wwid
        lines = process.system_output(cmd, sudo=True).strip("\n")
        for line in lines.split("\n"):
            if 'size' in line:
                return line.split("=")[1].split()[0]


def flush_path(path_name):
    """
    Flushes the given multipath.

    :return: Returns False if command fails, True otherwise.
    """
    cmd = "multipath -f %s" % path_name
    if process.system(cmd, ignore_status=True, sudo=True) != 0:
        return False
    return True
