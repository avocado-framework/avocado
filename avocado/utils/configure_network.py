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
from . import genio
from .ssh import Session

log = logging.getLogger('avocado.test')


class NWException(Exception):
    """
    Base Exception Class for all exceptions
    """


class NetworkInterface:

    """
    NetworkInterface, Provides  API's to Perform certain
    operation on a  Network Interface
    """

    def __init__(self, if_name):  # pylint: disable=W0231
        self.name = if_name

    def set_ip(self, ipaddr, netmask, interface_type=None):
        """
        Utility assign a IP  address (given to this utility ) to  Interface
        And generate interface file in sysfs based on distribution

        :param ipaddr : ip address which need to configure for interface
        :param netmask: Netmask which is associated  to provided IP
        :param interface_type: Interface type IPV4 or IPV6 , default is
                               IPV4 style
        """
        distro_name = distro.detect().name
        if distro_name == 'rhel':
            conf_file = "/etc/sysconfig/network-scripts/ifcfg-%s" % self.name
            self._move_config_file(conf_file, "%s.backup" % conf_file)
            with open(conf_file, "w") as network_conf:
                if interface_type is None:
                    interface_type = 'Ethernet'
                network_conf.write("TYPE=%s \n" % interface_type)
                network_conf.write("BOOTPROTO=none \n")
                network_conf.write("NAME=%s \n" % self.name)
                network_conf.write("DEVICE=%s \n" % self.name)
                network_conf.write("ONBOOT=yes \n")
                network_conf.write("IPADDR=%s \n" % ipaddr)
                network_conf.write("NETMASK=%s \n" % netmask)
                network_conf.write("IPV6INIT=yes \n")
                network_conf.write("IPV6_AUTOCONF=yes \n")
                network_conf.write("IPV6_DEFROUTE=yes")

        elif distro_name == 'SuSE':
            conf_file = "/etc/sysconfig/network/ifcfg-%s" % self.name
            self._move_config_file(conf_file, "%s.backup" % conf_file)
            with open(conf_file, "w") as network_conf:
                network_conf.write("IPADDR=%s \n" % ipaddr)
                network_conf.write("NETMASK='%s' \n" % netmask)
                network_conf.write("IPV6INIT=yes \n")
                network_conf.write("IPV6_AUTOCONF=yes \n")
                network_conf.write("IPV6_DEFROUTE=yes")
        else:
            raise NWException("Distro not supported by API , could not set ip")
        self.bring_up()

    def unset_ip(self):

        """Utility to unassign IP to Defined Interface"""

        if distro.detect().name == 'rhel':
            conf_file = "/etc/sysconfig/network-scripts/ifcfg-%s" % self.name

        if distro.detect().name == 'SuSE':
            conf_file = "/etc/sysconfig/network/ifcfg-%s" % self.name

        self.bring_down()
        self._move_config_file("%s.backup" % conf_file, conf_file)

    def ping_check(self, peer_ip, count, option=None, flood=False):
        """
        Utility perform ping operation on peer IP address and return status

        :param peer_ip :  Peer IP address
        :param count   :  ping count
        :param option  :  Default is None
        :param flood   :  Default is False
        """

        cmd = "ping -I %s %s -c %s" % (self.name, peer_ip, count)
        if flood:
            cmd = "%s -f" % cmd
        elif option:
            cmd = "%s %s" % (cmd, option)
        if process.system(cmd, shell=True, verbose=True,
                          ignore_status=True) != 0:
            return False
        return True

    def set_mtu_host(self, mtu):
        """
        Utility set mtu size to a interface and return status

        :param mtu :  mtu size that meed to be set
        :return : return True / False in case of mtu able to set
        """
        cmd = "ip link set %s mtu %s" % (self.name, mtu)
        try:
            process.system(cmd, shell=True)
        except process.CmdError as ex:
            raise NWException("MTU size can not be set: %s" % ex)
        try:
            cmd = "ip add show %s" % self.name
            mtuvalue = process.system_output(cmd, shell=True).decode("utf-8") \
                .split()[4]
            if mtuvalue == mtu:
                return True
        except Exception as ex:  # pylint: disable=W0703
            raise NWException("setting MTU value in host failed: %s" % ex)
        return False

    def is_link_up(self):
        """
        Checks if the interface link is up
        :return: True if the interface's link up, False otherwise.
        """
        if 'up' in genio.read_file("/sys/class/net/%s/operstate" % self.name):
            log.info("Interface %s link is up", self.name)
            return True
        return False

    def bring_up(self):

        """Utility used to Bring up interface"""

        cmd = "ifup %s" % self.name
        try:
            process.system(cmd, ignore_status=False, sudo=True)
            return True
        except process.CmdError as ex:
            raise NWException("ifup fails: %s" % ex)

    def bring_down(self):

        """Utility used to Bring down interface """

        cmd = "ifdown %s" % self.name
        try:
            process.system(cmd, sudo=True)
            return True
        except Exception as ex:
            raise NWException("ifdown fails: %s" % ex)

    def _move_config_file(self, src_conf, dest_conf):
        if os.path.exists(src_conf):
            shutil.move(src_conf, dest_conf)
        else:
            raise NWException("%s interface not available" % self.name)

    def get_hwaddr(self):
        try:
            with open('/sys/class/net/%s/address' % self.name, 'r') as fp:
                return fp.read().strip()
        except OSError as ex:
            raise NWException("interface not found : %s" % ex)

    def set_hwaddr(self, hwaddr):
        """
        Utility which set Hw address to Interface
        :param hwaddr: Pass Hardwae address for defined interface
        """
        try:
            process.system('ip link set %s address %s' %
                           (self.name, hwaddr))
        except Exception as ex:
            raise NWException("Setting Mac address failed: %s" % ex)

    def add_hwaddr(self, maddr):
        """
        Utility which add mac address to a interface return Status
        :param maddr: Mac address
        :return: True  Based on success if fail raise NWException
        """
        try:
            process.system('ip maddr add %s dev %s' % (maddr, self.name))
            return True
        except Exception as ex:
            raise NWException("Adding hw address fails: %s" % ex)

    def remove_hwaddr(self, maddr):
        """
        Utility remove mac address from interface and return Status
        :param maddr: Mac address
        :return:True on success if fail raise NWException
        """
        try:
            process.system('ip maddr del %s dev %s' % (maddr, self.name))
            return True
        except Exception as ex:
            raise NWException("ifdown fails: %s" % ex)


class PeerInfo:
    """
    class for peer function
    """

    def __init__(self, host, port=None, peer_user=None,
                 key=None, peer_password=None):
        """
        create a object for accesses remote machine
        """
        try:
            self.session = Session(host, port=port, user=peer_user,
                                   key=key, password=peer_password)
        except Exception as ex:  # pylint: disable=W0703
            raise NWException(
                "connection not established to peer machine: %s" % ex)

    def set_mtu_peer(self, peer_interface, mtu):
        """
        set MTU size in peer interface
        :param peer_interface :  Interface of peer system
        :return : status True when set otherwise False
        """
        cmd = "ip link set %s mtu %s" % (peer_interface, mtu)
        try:
            self.session.cmd(cmd)
            cmd = "ip add show %s" % peer_interface
            mtuvalue = self.session.cmd(cmd).stdout.decode("utf-8").split()[4]
            if mtuvalue == mtu:
                return True
        except Exception:  # pylint: disable=W0703
            return False

    def get_peer_interface(self, peer_ip):
        """
        get peer interface from peer ip
        :param peer_ip : IP address of Peer system
        :return        : Interface name of given IP in Peer system
                         get peer interface from peer ip
        """
        cmd = "ip addr show"
        try:
            for line in self.session.cmd(cmd).stdout.decode("utf-8") \
                                                    .splitlines():
                if peer_ip in line:
                    peer_interface = line.split()[-1]
        except Exception as ex:  # pylint: disable=W0703
            pass
        return peer_interface
