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
#
# Copyright: 2019 IBM
# Authors : Vaishnavi Bhat <vaishnavi@linux.vnet.ibm.com>

"""
Configure network when interface name and interface IP is available.
"""

import shutil
import os

from . import distro
from . import process


class NWException(Exception):
    """
    Base Exception Class for all exceptions
    """


def set_ip(ipaddr, netmask, interface):
    """
    Gets interface name, IP, subnet mask and creates interface
    file based on distro.
    """
    if distro.detect().name == 'rhel':
        conf_file = "/etc/sysconfig/network-scripts/ifcfg-%s" % interface
        if os.path.exists(conf_file):
            shutil.move(conf_file, conf_file+".backup")
        else:
            raise NWException("%s interface not available" % interface)
        with open(conf_file, "w") as network_conf:
            network_conf.write("TYPE=Ethernet \n")
            network_conf.write("BOOTPROTO=none \n")
            network_conf.write("NAME=%s \n" % interface)
            network_conf.write("DEVICE=%s \n" % interface)
            network_conf.write("ONBOOT=yes \n")
            network_conf.write("IPADDR=%s \n" % ipaddr)
            network_conf.write("NETMASK=%s" % netmask)

        cmd = "ifup %s" % interface
        try:
            process.system(cmd, ignore_status=False, sudo=True)
            return True
        except process.CmdError as ex:
            raise NWException("ifup fails: %s" % ex)

    if distro.detect().name == 'SuSE':
        conf_file = "/etc/sysconfig/ifcfg-%s" % interface
        if os.path.exists(conf_file):
            shutil.move(conf_file, conf_file+".backup")
        else:
            raise NWException("%s interface not available" % interface)
        with open(conf_file, "w") as network_conf:
            network_conf.write("IPADDR=%s \n" % ipaddr)
            network_conf.write("NETMASK=%s" % netmask)

        cmd = "ifup %s" % interface
        try:
            process.system(cmd, ignore_status=False, sudo=True)
            return True
        except process.CmdError as ex:
            raise NWException("ifup fails: %s" % ex)


def unset_ip(interface):
    """
    Gets interface name unassigns the IP to the interface
    """
    if distro.detect().name == 'rhel':
        conf_file = "/etc/sysconfig/network-scripts/ifcfg-%s" % interface

    if distro.detect().name == 'SuSE':
        conf_file = "/etc/sysconfig/ifcfg-%s" % interface

    cmd = "ifdown %s" % interface
    try:
        process.system(cmd, sudo=True)
        shutil.move(conf_file+".backup", conf_file)
        return True
    except Exception as ex:
        raise NWException("ifdown fails: %s" % ex)
