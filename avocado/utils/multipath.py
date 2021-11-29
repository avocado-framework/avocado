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

import ast
import logging
import time

from avocado.utils import distro, process, service, wait

LOG = logging.getLogger(__name__)


class MPException(Exception):
    """
    Base Exception Class for all exceptions
    """


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
    LOG.debug(open(conf_file, "r").read())
    # The reason for sleep here is to give some time for change in
    # multipath.conf file to take effect.
    time.sleep(5)
    mpath_svc = service.SpecificServiceManager(get_svc_name())
    mpath_svc.restart()
    wait.wait_for(mpath_svc.status, timeout=10)


def device_exists(mpath):
    """
    Checks if a given mpath exists.

    :param mpath: The multipath path
    :return: True if path exists, False if does not exist.
    :rtype: bool
    """
    cmd = "multipath -ll"
    out = process.run(cmd, ignore_status=True, sudo=True,
                      shell=True).stdout_text
    if mpath in out:
        return True
    return False


def get_mpath_name(wwid):
    """
    Get multipath name for a given wwid.

    :param wwid: wwid of multipath device.
    :return: Name of multipath device.
    :rtype: str
    """
    if device_exists(wwid):
        cmd = "multipath -l %s" % wwid
        return process.run(cmd,
                           sudo=True).stdout_text.split()[0]


def get_multipath_wwids():
    """
    Get list of multipath wwids.

    :return: List of multipath wwids.
    :rtype: list of str
    """
    cmd = "egrep -v '^($|#)' /etc/multipath/wwids"
    wwids = process.run(cmd, ignore_status=True,
                        sudo=True, shell=True).stdout_text
    wwids = wwids.strip("\n").replace("/", "").split("\n")
    return wwids


def get_multipath_wwid(mpath):
    """
    Get the wwid binding for given mpath name

    :return: Multipath wwid
    :rtype: str
    """
    cmd = "multipathd show maps format '%n %w'"
    try:
        wwids = process.run(cmd, ignore_status=True,
                            sudo=True, shell=True).stdout_text
    except process.CmdError as ex:
        raise MPException("Multipathd Command Failed : %s " % ex)
    for wwid in wwids.splitlines():
        if mpath in wwid:
            return wwid.split()[1]


def is_mpath_dev(mpath):
    """
    Check the give name is a multipath device name or not.

    :return: True if device is multipath or False
    :rtype: Boolean
    """
    cmd = "multipath -l -v 1"
    try:
        mpaths = process.run(cmd, ignore_status=True,
                             sudo=True, shell=True).stdout_text
    except process.CmdError as ex:
        raise MPException("Multipath Command Failed : %s " % ex)
    if mpath in mpaths.strip('\n').split("\n"):
        return True
    return False


def get_paths(wwid):
    """
    Get list of paths, given a multipath wwid.

    :return: List of paths.
    :rtype: list of str
    """
    if not device_exists(wwid):
        return
    cmd = "multipath -ll %s" % wwid
    lines = process.run(cmd,
                        sudo=True).stdout_text.strip("\n")
    paths = []
    for line in lines.split("\n"):
        if not (('size' in line) or ('policy' in line) or (wwid in line)):
            paths.append(line.split()[-5])
    return paths


def get_multipath_details():
    """
    Get multipath details as a dictionary.

    This is the output of the following command:

      $ multipathd show maps json

    :return: Dictionary of multipath output in json format
    :rtype: dict
    """
    mpath_op = process.run("multipathd show maps json",
                           sudo=True, verbose=False).stdout_text
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
                          ignore_status=True, shell=True):
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
    Fail the individual paths.

    :param str path: disk path. Example: sda, sdb.
    :return: True if succeeded, False otherwise
    :rtype: bool
    """
    def is_failed():
        path_stat = get_path_status(path)
        if path_stat[0] == 'failed' and path_stat[2] == 'faulty':
            return True
        return False

    cmd = 'multipathd -k"fail path %s"' % path
    if process.system(cmd) == 0:
        return wait.wait_for(is_failed, timeout=10) or False
    return False


def reinstate_path(path):
    """
    Reinstate the individual paths.

    :param str path: disk path. Example: sda, sdb.
    :return: True if succeeded, False otherwise
    """
    def is_reinstated():
        path_stat = get_path_status(path)
        if path_stat[0] == 'active' and path_stat[2] == 'ready':
            return True
        return False
    cmd = 'multipathd -k"reinstate path %s"' % path
    if process.system(cmd) == 0:
        return wait.wait_for(is_reinstated, timeout=10) or False
    return False


def get_policy(wwid):
    """
    Gets path_checker policy, given a multipath wwid.

    :return: path checker policy.
    :rtype: str
    """
    if device_exists(wwid):
        cmd = "multipath -ll %s" % wwid
        lines = process.run(cmd, sudo=True).stdout_text.strip("\n")
        for line in lines.split("\n"):
            if 'policy' in line:
                return line.split("'")[1].split()[0]


def get_size(wwid):
    """
    Gets size of device, given a multipath wwid.

    :return: size of multipath device.
    :rtype: str
    """
    if device_exists(wwid):
        cmd = "multipath -ll %s" % wwid
        lines = process.run(cmd, sudo=True).stdout_text.strip("\n")
        for line in lines.split("\n"):
            if 'size' in line:
                return line.split("=")[1].split()[0]


def flush_path(path_name):
    """
    Flushes the given multipath.

    :return: Returns False if command fails, True otherwise.
    """
    cmd = "multipath -f %s" % path_name
    if process.system(cmd, ignore_status=True, sudo=True, shell=True):
        return False
    return True


def get_mpath_status(mpath):
    """
    Get the status of mpathX of multipaths.

    :param mpath: mpath names. Example: mpatha, mpathb.
    :return: state of mpathX eg: Active, Suspend, None
    """
    cmd = 'multipathd -k"show maps status" | grep -i %s' % mpath
    mpath_status = process.getoutput(cmd).split()[-2]
    return mpath_status


def suspend_mpath(mpath):
    """
    Suspend the given mpathX of multipaths.

    :param mpath: mpath names. Example: mpatha, mpathb.
    :return: True or False
    """
    def is_mpath_suspended():
        if get_mpath_status(mpath) == 'suspend':
            return True
        return False

    cmd = 'multipathd -k"suspend map %s"' % mpath
    if process.system(cmd) == 0:
        return wait.wait_for(is_mpath_suspended, timeout=10) or False
    return False


def resume_mpath(mpath):
    """
    Resume the suspended mpathX of multipaths.

    :param mpath_name: mpath names. Example: mpatha, mpathb.
    :return: True or False
    """
    def is_mpath_resumed():
        if get_mpath_status(mpath) == 'active':
            return True
        return False

    cmd = 'multipathd -k"resume map %s"' % mpath
    if process.system(cmd) == 0:
        return wait.wait_for(is_mpath_resumed, timeout=10) or False
    return False


def remove_mpath(mpath):
    """
    Remove the mpathX of multipaths.

    :param mpath_name: mpath names. Example: mpatha, mpathb.
    :return: True or False
    """
    def is_mpath_removed():
        if device_exists(mpath):
            return False
        return True

    cmd = 'multipathd -k"remove map %s"' % mpath
    if process.system(cmd) == 0:
        return wait.wait_for(is_mpath_removed, timeout=10) or False
    return False


def add_mpath(mpath):
    """
    Add back the removed mpathX of multipath.

    :param mpath_name: mpath names. Example: mpatha, mpathb.
    :return: True or False
    """
    def is_mpath_added():
        if device_exists(mpath):
            return True
        return False

    cmd = 'multipathd -k"add map %s"' % mpath
    if process.system(cmd) == 0:
        return wait.wait_for(is_mpath_added, timeout=10) or False
    return False


def remove_path(path):
    """
    Remove the individual paths.

    :param disk_path: disk path. Example: sda, sdb.
    :return: True or False
    """
    def is_path_removed():
        if get_path_status(path) is None:
            return True
        return False

    cmd = 'multipathd -k"remove path %s"' % path
    if process.system(cmd) == 0:
        return wait.wait_for(is_path_removed, timeout=10) or False
    return False


def add_path(path):
    """
    Add back the removed individual paths.

    :param str path: disk path. Example: sda, sdb.
    :return: True or False
    """
    def is_path_added():
        if get_path_status(path) is None:
            return False
        return True

    cmd = 'multipathd -k"add path %s"' % path
    if process.system(cmd) == 0:
        return wait.wait_for(is_path_added, timeout=10) or False
    return False
