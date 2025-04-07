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
# This code was inspired in the autotest project,
#
# client/base_utils.py
#
# Copyright: IBM, 2019
#            Red Hat Inc. 2019
# Authors : Praveen K Pandey <praveen@linux.vnet.ibm.com>
#           Cleber Rosa <crosa@redhat.com>


"""
Linux OS utilities
"""

import os

from avocado.utils import genio, process


class UnsupportedMachineError(Exception):
    """
    Exception class for unsupported hardware
    """


def get_proc_sys(key):
    """
    Read values from /proc/sys

    :param key: A location under /proc/sys
    :return: The single-line sysctl value as a string.
    """
    path = os.path.join("/proc/sys/%s", key)
    return genio.read_one_line(path)


def set_proc_sys(key, value):
    """
    Set values on /proc/sys

    :param key: A location under /proc/sys
    :param value: If not None, a value to write into the sysctl.

    :return: The single-line sysctl value as a string.
    """
    path = os.path.join("/proc/sys/%s", key)
    genio.write_one_line(path, value)
    return get_proc_sys(key)


def is_selinux_enforcing():
    """
    Returns True if SELinux is in enforcing mode, False if permissive/disabled.
    """
    if "1" in genio.read_one_line("/sys/fs/selinux/enforce"):
        return True
    return False


def enable_selinux_enforcing():
    """
    Enable  SELinux Enforcing in system

    :return: True if SELinux enable in enforcing mode, False if not enabled
    """
    genio.write_one_line("/sys/fs/selinux/enforce", "1")
    if is_selinux_enforcing():
        return True
    return False


def is_os_secureboot_enabled():
    """
    Check whether the secure-boot is enabled at os level.
    Check for "00000002" in "/proc/device-tree/ibm,secure-boot" file
    If found, then secure-boot is enabled.

    :return: True if secureboot is enabled, False if otherwise
    """
    try:
        cmd = "lsprop /proc/device-tree/ibm,secure-boot"
        for line in process.system_output(cmd).decode("utf-8").splitlines():
            if "00000002" in line:
                return True
    except FileNotFoundError as exc:
        raise UnsupportedMachineError("lsprop not a supported command") from exc
    return False


def is_sched_schedstats_enabled():
    """
    Returns True if sched_schedstats is in enabled  mode, False if no.
    """
    if "1" in genio.read_one_line("/proc/sys/kernel/sched_schedstats"):
        return True
    return False


def enable_sched_schedstats():
    """
    Enable  SELinux Enforcing in system

    :return: True if sched_schedstats enabled , False if not enabled
    """
    genio.write_one_line("/proc/sys/kernel/sched_schedstats", "1")
    if is_sched_schedstats_enabled():
        return True
    return False
