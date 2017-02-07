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
#
# Author: Kleber Sacilotto de Souza <klebers@linux.vnet.ibm.com>
# Author: Daniel Kreling <kreling@linux.vnet.ibm.com>
# for get_memory_address() and get_mask()

"""
Module for all PCI devices related functions.
"""


import re
import os
from .genio import read_file
from . import process


def get_domains():
    """
    Gets all PCI domains.
    Example, it returns ['0000', '0001', ...]

    :return: List of PCI domains.
    """
    cmd = "lspci -D"
    output = process.system_output(cmd, ignore_status=True)
    if output:
        domains = []
        for line in output.splitlines():
            domains.append(line.split(":")[0])
        return list(set(domains))


def get_pci_addresses():
    """
    Gets list of PCI addresses in the system.
    Does not return the PCI Bridges/Switches.

    :return: list of full PCI addresses including domain (0000:00:14.0)
    """
    addresses = []
    cmd = "lspci -D"
    for line in process.system_output(cmd).splitlines():
        if "PCI bridge" not in line:
            addresses.append(line.split()[0])
    if addresses:
        return addresses


def get_num_interfaces_in_pci(dom_pci_address):
    """
    Gets number of interfaces of a given partial PCI address starting with
    full domain address.

    :param dom_pci_address: Partial PCI address including domain
                            address (0000, 0000:00:1f, 0000:00:1f.2, etc)

    :return: number of devices in a PCI domain.
    """
    cmd = "ls -l /sys/class/*/ -1"
    output = process.system_output(cmd, ignore_status=True, shell=True)
    if output:
        filt = '/%s' % dom_pci_address
        count = 0
        for line in output.splitlines():
            if filt in line:
                count += 1
        return count


def get_disks_in_pci_address(pci_address):
    """
    Gets disks in a PCI address.

    :param pci_address: Any segment of a PCI address (1f, 0000:00:1f, ...)

    :return: list of disks in a PCI address.
    """
    disks_path = "/dev/disk/by-path/"
    disk_list = []
    for dev in os.listdir(disks_path):
        if pci_address in dev:
            link = os.readlink(os.path.join(disks_path, dev))
            disk_list.append(os.path.abspath(os.path.join(disks_path, link)))
    return disk_list


def get_nics_in_pci_address(pci_address):
    """
    Gets network interface(nic) in a PCI address.

    :param pci_address: Any segment of a PCI address (1f, 0000:00:1f, ...)

    :return: list of network interfaces in a PCI address.
    """
    iface_path = "/sys/class/net/"
    net_interfaces_list = []
    for iface in os.listdir(iface_path):
        if pci_address in os.readlink("%s%s" % (iface_path, iface)):
            net_interfaces_list.append(iface)
    return net_interfaces_list


def get_pci_fun_list(pci_address):
    """
    Gets list of functions in the given PCI address.
    Example: in address 0000:03:00, functions are 0000:03:00.0 and 0000:03:00.1

    :param pci_address: Any segment of a PCI address (1f, 0000:00:1f, ...)

    :return: list of functions in a PCI address.
    """
    return list(dev for dev in get_pci_addresses() if pci_address in dev)


def get_slot_from_sysfs(full_pci_address):
    """
    Gets the PCI slot of given address.

    :note: Specific for ppc64 processor.

    :param full_pci_address: Full PCI address including domain (0000:03:00.0)

    :return: slot of PCI address from sysfs.
    """
    if not os.path.isfile('/sys/bus/pci/devices/%s/devspec' % full_pci_address):
        return
    devspec = read_file("/sys/bus/pci/devices/%s/devspec" % full_pci_address)
    if not os.path.isfile("/proc/device-tree/%s/ibm,loc-code" % devspec):
        return
    slot = read_file("/proc/device-tree/%s/ibm,loc-code" % devspec)
    return re.match(r'((\w+)[\.])+(\w+)-(\w*\d+)-(\w*\d+)|Slot(\d+)',
                    slot).group()


def get_slot_list():
    """
    Gets list of PCI slots in the system.

    :note: Specific for ppc64 processor.

    :return: list of slots in the system.
    """
    return list(set(get_slot_from_sysfs(dev) for dev in get_pci_addresses()))


def get_pci_id_from_sysfs(full_pci_address):
    """
    Gets the PCI ID from sysfs of given PCI address.

    :param full_pci_address: Full PCI address including domain (0000:03:00.0)

    :return: PCI ID of a PCI address from sysfs.
    """
    path = "/sys/bus/pci/devices/%s" % full_pci_address
    if os.path.isdir(path):
        path = "%s/%%s" % path
        return ":".join(["%04x" % int(open(path % param).read(), 16)
                         for param in ['vendor', 'device', 'subsystem_vendor',
                                       'subsystem_device']])


def get_pci_prop(pci_address, prop):
    """
    Gets specific PCI ID of given PCI address. (first match only)

    :param pci_address: Any segment of a PCI address (1f, 0000:00:1f, ...)
    :param part: prop of PCI ID.

    :return: specific PCI ID of a PCI address.
    """
    cmd = "lspci -Dnvmm -s %s" % pci_address
    output = process.system_output(cmd, ignore_status=True)
    if output:
        for line in output.splitlines():
            if prop == line.split(':')[0]:
                return line.split()[-1]


def get_pci_id(pci_address):
    """
    Gets PCI id of given address. (first match only)

    :param pci_address: Any segment of a PCI address (1f, 0000:00:1f, ...)

    :return: PCI ID of a PCI address.
    """
    pci_id = []
    for params in ['Vendor', 'Device', 'SVendor', 'SDevice']:
        output = get_pci_prop(pci_address, params)
        if not output:
            return
        pci_id.append(output)
    if pci_id:
        return ":".join(pci_id)


def get_driver(pci_address):
    """
    Gets the kernel driver in use of given PCI address. (first match only)

    :param pci_address: Any segment of a PCI address (1f, 0000:00:1f, ...)

    :return: driver of a PCI address.
    """
    cmd = "lspci -ks %s" % pci_address
    output = process.system_output(cmd, ignore_status=True)
    if output:
        for line in output.splitlines():
            if 'Kernel driver in use:' in line:
                return line.rsplit(None, 1)[-1]


def get_memory_address(pci_address):
    """
    Gets the memory address of a PCI address. (first match only)

    :note: There may be multiple memory address for a PCI address.
    :note: This function returns only the first such address.

    :param pci_address: Any segment of a PCI address (1f, 0000:00:1f, ...)

    :return: memory address of a pci_address.
    """
    cmd = "lspci -bv -s %s" % pci_address
    output = process.system_output(cmd, ignore_status=True)
    if output:
        for line in output.splitlines():
            if 'Memory at' in line:
                return "0x%s" % line.split()[2]


def get_mask(pci_address):
    """
    Gets the mask of PCI address. (first match only)

    :note: There may be multiple memory entries for a PCI address.
    :note: This mask is calculated only with the first such entry.

    :param pci_address: Any segment of a PCI address (1f, 0000:00:1f, ...)

    :return: mask of a PCI address.
    """
    cmd = "lspci -vv -s %s" % pci_address
    output = process.system_output(cmd, ignore_status=True)
    if output:
        dic = {'K': 1024, 'M': 1048576, 'G': 1073741824}
        for line in output.splitlines():
            if 'Region' in line and 'Memory at' in line:
                val = line.split('=')[-1].split(']')[0]
                memory_size = int(val[:-1]) * dic[val[-1]]
                break
        # int("0xffffffff", 16) = 4294967295
        mask = hex((memory_size - 1) ^ 4294967295)
        return mask


def get_vpd(dom_pci_address):
    """
    Gets the VPD (Virtual Product Data) of the given PCI address.

    :note: Specific for ppc64 processor.

    :param dom_pci_address: Partial PCI address including domain addr and at
                            least bus addr (0003:00, 0003:00:1f.2, ...)

    :return: dictionary of VPD of a PCI address.
    """
    cmd = "lsvpd -l %s" % dom_pci_address
    vpd = process.system_output(cmd)
    vpd_dic = {}
    dev_list = []
    for line in vpd.splitlines():
        if len(line) < 5:
            continue
        if '*YL' in line:
            vpd_dic['slot'] = line[4:]
        elif '*DS' in line:
            vpd_dic['pci_id'] = line[4:]
        elif '*FC' in line:
            vpd_dic['feature_code'] = line[4:]
        elif '*AX' in line:
            if not (dom_pci_address in line or
                    vpd_dic['pci_id'].split()[0] in line):
                dev_list.append(line[4:])
        elif '*CD' in line:
            vpd_dic['pci_id'] = line[4:]
    vpd_dic['devices'] = dev_list
    return vpd_dic


def get_cfg(dom_pci_address):
    """
    Gets the hardware configuration data of the given PCI address.

    :note: Specific for ppc64 processor.

    :param dom_pci_address: Partial PCI address including domain addr and at
                            least bus addr (0003:00, 0003:00:1f.2, ...)

    :return: dictionary of configuration data of a PCI address.
    """
    cmd = "lscfg -vl %s" % dom_pci_address
    cfg = process.system_output(cmd)
    cfg_dic = {}
    desc = re.match(r'  (%s)( [-\w+,\.]+)+([ \n])+([-\w+, \(\)])+'
                    % dom_pci_address, cfg).group()
    cfg_dic['Description'] = desc
    for line in cfg.splitlines():
        if 'Manufacturer Name' in line:
            cfg_dic['Mfg'] = line.split('.')[-1]
        if 'Machine Type-Model' in line:
            cfg_dic['Model'] = line.split('.')[-1]
        if 'Device Specific' in line:
            cfg_dic['YC'] = line.split('.')[-1]
        if 'Location Code' in line:
            cfg_dic['YL'] = line.split('..')[-1].strip('.')
    return cfg_dic
