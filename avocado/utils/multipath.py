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
from . import distro
from . import process
from . import service


def form_conf_mpath_file(blacklist="", defaults_extra=""):
    """
    Form a multipath configuration file, and restart multipath service.

    :parm blacklist: Entry in conf file to indicate blacklist section.
    :parm defaults_extra: Extra entry in conf file in defaults section.
    """
    mpath_fp = open("/etc/multipath.conf", "w")
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
    mpath_fp.close()
    logging.debug(open("/etc/multipath.conf", "r").read())
    if distro.detect().name == 'Ubuntu':
        svc_name = "multipath-tools"
    else:
        svc_name = "multipathd"
    time.sleep(5)
    service.SpecificServiceManager(svc_name).restart()


def device_exists(path):
    """
    Checks if a given path exists.

    :return: True if path exists, False if does not exist.
    """
    cmd = "multipath -l %s" % path
    if process.system(cmd, ignore_status=True) != 0:
        return False
    return True


def get_mpath_name(wwid):
    """
    Get multipath name for a given wwid.

    :parm wwid: wwid of multipath device.

    :return: Name of multipath device.
    """
    if not device_exists(wwid):
        return
    cmd = "multipath -l %s" % wwid
    return process.system_output(cmd).split()[0]


def get_multipath_wwids():
    """
    Get list of multipath wwids.

    :return: List of multipath wwids.
    """
    cmd = "egrep -v '^($|#)' /etc/multipath/wwids"
    wwids = process.system_output(cmd, ignore_status=True).strip("\n")
    wwids = wwids.replace("/", "").split("\n")
    return wwids


def get_paths(wwid):
    """
    Get list of paths, given a multipath wwid.

    :return: List of paths.
    """
    if not device_exists(wwid):
        return
    cmd = "multipath -ll %s" % wwid
    lines = process.system_output(cmd).strip("\n")
    paths = []
    for line in lines.split("\n"):
        if not (('size' in line) or ('policy' in line) or (wwid in line)):
            paths.append(line.split()[-5])
    return paths


def get_policy(wwid):
    """
    Gets path_checker policy, given a multipath wwid.

    :return: path checker policy.
    """
    if not device_exists(wwid):
        return
    cmd = "multipath -ll %s" % wwid
    lines = process.system_output(cmd).strip("\n")
    for line in lines.split("\n"):
        if 'policy' in line:
            return line.split("'")[1].split()[0]
    return ""


def get_size(wwid):
    """
    Gets size of device, given a multipath wwid.

    :return: size of multipath device.
    """
    if not device_exists(wwid):
        return
    cmd = "multipath -ll %s" % wwid
    lines = process.system_output(cmd).strip("\n")
    for line in lines.split("\n"):
        if 'size' in line:
            return line.split("=")[1].split()[0]
    return ""


def flush_path(path_name):
    """
    Flushes the given multipath.

    :return: Returns False if command fails, True otherwise.
    """
    cmd = "multipath -f %s" % path_name
    if process.system(cmd, ignore_status=True) != 0:
        return False
    return True
