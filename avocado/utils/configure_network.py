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

import logging
from . import distro
from . import process
from .ssh import Session

log = logging.getLogger('avocado.test')


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


class HostInfo:
    """
    class for host function
    """

    def ping_check(self, interface, peer_ip, count, option=None, flood=False):
        """
        Checks if the ping to peer works.
        """
        cmd = "ping -I %s %s -c %s" % (interface, peer_ip, count)
        if flood is True:
            cmd = "%s -f" % cmd
        elif option is not None:
            cmd = "%s %s" % (cmd, option)
        if process.system(cmd, shell=True, verbose=True,
                          ignore_status=True) != 0:
            return False
        return True

    def set_mtu_host(self, interface, mtu):
        """
        set mtu size in host interface
        """
        cmd = "ip link set %s mtu %s" % (interface, mtu)
        try:
            process.system(cmd, shell=True)
        except process.CmdError as ex:
            raise NWException("mtu size can not be set: %s" % ex)
        try:
            cmd = "ip add show %s" % interface
            mtuvalue = process.system_output(cmd, shell=True).decode("utf-8") \
                                                             .split()[4]
            if mtuvalue == mtu:
                return True
        except Exception as ex:
            log.error("setting mtu value in host failed: %s", ex)
        return False


class PeerInfo:
    """
    class for peer function
    """

    def __init__(self, host, port=None, peer_user=None,
                 key=None, peer_password=None):
        """
        create a object for acsses remote machnine
        """
        try:
            self.session = Session(host, port=port, user=peer_user,
                                   key=key, password=peer_password)
        except Exception as ex:
            log.error("connection not established to peer machine: %s", ex)

    def set_mtu_peer(self, peer_interface, mtu):
        """
        set mtu size in peer interface
        """
        cmd = "ip link set %s mtu %s" % (peer_interface, mtu)
        try:
            self.session.cmd(cmd)
            cmd = "ip add show %s" % peer_interface
            mtuvalue = self.session.cmd(cmd).stdout.decode("utf-8").split()[4]
            if mtuvalue == mtu:
                return True
        except Exception as ex:
            log.error("setting mtu value in peer failed: %s", ex)
        return False

    def get_peer_interface(self, peer_ip):
        """
        get peer interface from peer ip
        """
        cmd = "ip addr show"
        try:
            for line in self.session.cmd(cmd).stdout.decode("utf-8") \
                                                    .splitlines():
                if peer_ip in line:
                    peer_interface = line.split()[-1]
        except Exception as ex:
            if peer_interface == "":
                log.error("unable to get peer interface: %s", ex)
        else:
            return peer_interface
