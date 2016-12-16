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
from . import process


def get_domains():
    """
    Gets all pci domains.

    :return: List of pci domains.
    """
    cmd = "lspci -D | awk -F: {'print $1'} | uniq"
    domains = process.system_output(cmd, shell=True, ignore_status=True)
    if domains:
        return domains.splitlines()


def get_num_devices_in_domain(domain):
    """
    Gets number of devices in a pci domain.

    :parm domain: pci domain.

    :return: number of devices in a pci domain.
    """
    cmd = "ls -l /sys/class/*/ -1 | grep -i %s | wc -l" % domain
    num_devices = process.system_output(cmd, shell=True, ignore_status=True)
    return num_devices


def get_disks_in_device(device):
    """
    Gets disks in a pci device.

    :parm device: pci device.

    :return: list of disks in a pci device.
    """
    cmd = "ls -l /dev/disk/by-path/ | grep %s | awk '{print $NF}'" % device
    devices = process.system_output(cmd, shell=True, ignore_status=True)
    devices_list = []
    if devices:
        for dev in devices.splitlines():
            cmd = "realpath -s /dev/disk/by-path/%s" % dev
            dev = process.system_output(cmd, shell=True, ignore_status=True)
            devices_list.append(dev.strip('\n'))
    return devices_list


def get_interfaces_in_device(device):
    """
    Gets ethernet interface in a pci device.

    :parm device: pci device.

    :return: list of interfaces in a pci device.
    """
    cmd = "ls -l /sys/class/net/ | grep %s | awk '{print $NF}'" % device
    devices = process.system_output(cmd, shell=True, ignore_status=True)
    interfaces_list = []
    if devices:
        for dev in devices.splitlines():
            interfaces_list.append(dev.split("/")[-1])
    return interfaces_list


def get_pci_fun_list(device):
    """
    Gets list of functions in the given pci device.
    Example: in device 0000:03:00, functions are 0000:03:00.0 and 0000:03:00.1

    :parm device: pci device.

    :return: list of functions in a pci device.
    """
    cmd = "lspci -D | grep %s | awk {'print $1'}" % device
    functions = process.system_output(cmd, shell=True, ignore_status=True)
    if functions:
        return functions.splitlines()


def get_slot_from_sysfs(device):
    """
    Gets the pci slot of given device.

    :parm device: pci device.

    :return: slot of pci device from sysfs.
    """
    if not os.path.isdir('/sys/bus/pci/devices/%s' % device):
        return
    cmd = "cat /sys/bus/pci/devices/%s/devspec ; echo" % device
    devspec = process.system_output(cmd, shell=True).strip('\n')
    cmd = "cat /proc/device-tree/%s/ibm,loc-code ; echo" % devspec
    slot = process.system_output(cmd, shell=True).strip('\0\n')
    return re.match(r'((\w+)[\.])+(\w+)-(\w*\d+)-(\w*\d+)|Slot(\d+)',
                    slot).group()


def get_pci_id_from_sysfs(device):
    """
    Gets the pci id from sysfs of given device.

    :parm device: pci device.

    :return: pci id of a pci device from sysfs.
    """
    if not os.path.isdir('/sys/bus/pci/devices/%s' % device):
        return
    pci_id = ""
    for params in ['vendor', 'device', 'subsystem_vendor', 'subsystem_device']:
        cmd = "cat /sys/bus/pci/devices/%s/%s" % (device, params)
        p_id = process.system_output(cmd, shell=True).strip('\n').strip('0x')
        while len(p_id) < 4:
            p_id = "0%s" % p_id
        pci_id += "%s:" % p_id
    if pci_id:
        return pci_id[:-1]


def get_slot_list():
    """
    Gets list of pci slots in the system.

    :return: list of slots in the system.
    """
    slot_list = []
    for device in get_pci_devices():
        slot_list.append(get_slot_from_sysfs(device))
    return list(set(slot_list))


def get_specific_pci_id(device, part):
    """
    Gets specific pci id of given divice.

    :parm device: pci device.
    :parm part: part of pci id.

    :return: specific pci id of a pci device.
    """
    cmd = "lspci -Dnvmm -s %s | grep -iw %s" % (device, part)
    output = process.system_output(cmd, shell=True, ignore_status=True)
    if not output:
        return
    return output.split()[-1]


def get_pci_id(device):
    """
    Gets pci id of given divice.

    :parm device: pci device.

    :return: pci id of a pci device.
    """
    pci_id = ""
    for params in ['Vendor', 'Device', 'SVendor', 'SDevice']:
        output = get_specific_pci_id(device, params)
        if output:
            pci_id += "%s:" % output
    if pci_id:
        return pci_id[:-1]


def get_memory_address(device):
    """
    Gets the memory address of a pci device.

    :parm device: pci device.

    :return: memory address of a pci device.
    """
    cmd = "lspci -bv -s %s" % device
    output = process.system_output(cmd, shell=True, ignore_status=True)
    if not output:
        return
    for line in output.splitlines():
        if 'Memory at' in line:
            return "0x%s" % line.split()[2]


def get_mask(device):
    """
    Gets the mask of pci device.

    :parm device: pci device.

    :return: mask of a pci device.
    """
    cmd = "lspci -vv -s %s" % device
    output = process.system_output(cmd, shell=True, ignore_status=True)
    if not output:
        return
    dic = {'K': '10', 'M': '20', 'G': '30'}
    for line in output.splitlines():
        if 'Region' in line and 'Memory at' in line:
            val = line.split('=')[-1].split(']')[0]
            memory_size = int(val[:-1]) * pow(2, int(dic[val[-1]]))
            break
    mask = hex((memory_size - 1) ^ int("0xffffffff", 16))
    return mask


def get_pci_devices():
    """
    Gets list of pci devices in the system.

    :return: list of pci devices.
    """
    cmd = "lspci -D | grep -iv 'pci bridge' | awk '{print $1}'"
    devices = process.system_output(cmd, shell=True, ignore_status=True)
    if devices:
        return devices.splitlines()


def get_vpd(device):
    """
    Gets the vpd of the given device.

    :parm device: pci device.

    :return: dictionary of vpd of a pci device.
    """
    cmd = "lsvpd -l %s" % device
    vpd = process.system_output(cmd, shell=True)
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
            if not (device in line or vpd_dic['pci_id'].split()[0] in line):
                dev_list.append(line[4:])
    vpd_dic['devices'] = dev_list
    return vpd_dic


def get_cfg(device):
    """
    Gets the cfg data of the given device.

    :parm device: pci device.

    :return: dictionary of cfg data of a pci device.
    """
    cmd = "lscfg -vl %s" % device
    cfg = process.system_output(cmd, shell=True)
    cfg_dic = {}
    desc = re.match(r'  (%s)( [-\w+,\.]+)+([ \n])+([-\w+, \(\)])+' % device,
                    cfg).group()
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
