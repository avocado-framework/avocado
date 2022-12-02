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
# Copyright: 2022 IBM
# Authors : Naresh Bannoth <nbannoth@linux.vnet.ibm.com>


"""
Nvme utilities
"""


import os

from avocado.utils import pci, process


class NvmeError(Exception):
    """
    nvme DiskError
    """


def get_controller_name(pci_addr):
    """
    Returns the controller/Adapter name with the help of pci_address

    :param pci_addr: pci_address of the adapter
    :rtype: string
    :raises: :py:class:`NvmeError` on failure to find pci_address in OS
    """
    if pci_addr in pci.get_pci_addresses():
        path = f"/sys/bus/pci/devices/{pci_addr}/nvme/"
        return os.listdir(path)
    raise NvmeError("Unable to list as wrong pci_addr")


def get_number_of_ns_supported(controller_name):
    """
    Returns the number of namespaces supported for the nvme adapter

    :param controller_name: Name of the controller eg: nvme0
    :rtype: integer
    """
    cmd = f"nvme id-ctrl /dev/{controller_name}"
    out = process.run(cmd, ignore_status=True, sudo=True, shell=True).stdout_text
    for line in out.splitlines():
        if line.split(":")[0].strip() == "nn":
            return int(line.split(":")[-1].strip())
    return ""


def get_total_capacity(controller_name):
    """
    Returns the total capacity of the nvme adapter

    :param controller_name: Name of the controller eg: nvme0
    :rtype: integer
    """
    cmd = f"nvme id-ctrl /dev/{controller_name}"
    out = process.run(cmd, ignore_status=True, sudo=True, shell=True).stdout_text
    for line in out.splitlines():
        if line.split(":")[0].strip() == "tnvmcap":
            return int(line.split(":")[-1].strip())
    return ""


def get_controller_id(controll_name):
    """
    Returns the nvme controller id

    :param controller_name: Name of the controller eg: nvme0
    :rtype: string
    """
    cmd = f"nvme list-ctrl /dev/{controll_name}"
    output = process.system_output(cmd, shell=True, ignore_status=True).decode("utf-8")
    for line in output.splitlines():
        if "0]" in line:
            return line.split(":")[-1]
    return ""
