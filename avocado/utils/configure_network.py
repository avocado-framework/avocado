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
    class For network interface
    """

    def __init__(self, interface):
        self._interface = interface

    def set_ip(self, ipaddr, netmask, interface_type=None):
        """
        Utility Assign a IP  address (given to this utility ) to  Interface

        :param ipaddr : ip address which need to configure for interface
        :param netmask: Netmask which is associated  to provided IP
        :param interface_type: Interface type IPV4 or IPV6 , default is
                               IPV4 style
        """
        if distro.detect().name == 'rhel':
            conf_file = "/etc/sysconfig/network-scripts/ifcfg-%s" % self._interface
            self._move_interfaceconfile(conf_file, "%s.backup" % conf_file)
            with open(self._confile, "w") as network_conf:
                if interface_type is None:
                    interface_type = 'Ethernet'
                network_conf.write("TYPE=%s \n" % interface_type)
                network_conf.write("BOOTPROTO=none \n")
                network_conf.write("NAME=%s \n" % self._interface)
                network_conf.write("DEVICE=%s \n" % self._interface)
                network_conf.write("ONBOOT=yes \n")
                network_conf.write("IPADDR=%s \n" % ipaddr)
                network_conf.write("NETMASK=%s \n" % netmask)
                network_conf.write("IPV6INIT=yes \n")
                network_conf.write("IPV6_AUTOCONF=yes \n")
                network_conf.write("IPV6_DEFROUTE=yes")

        if distro.detect().name == 'SuSE':
            conf_file = "/etc/sysconfig/network/ifcfg-%s" % self._interface
            self._move_interfaceconfile(conf_file, "%s.backup" % conf_file)
            with open(self._confile, "w") as network_conf:
                network_conf.write("IPADDR=%s \n" % ipaddr)
                network_conf.write("NETMASK='%s' \n" % netmask)
                network_conf.write("IPV6INIT=yes \n")
                network_conf.write("IPV6_AUTOCONF=yes \n")
                network_conf.write("IPV6_DEFROUTE=yes")
        self.bring_up()

    def unset_ip(self):
        """
        Unassign IP to Defined Interface
        """
        conf_file = ''
        if distro.detect().name == 'rhel':
            conf_file = "/etc/sysconfig/network-scripts/ifcfg-%s" % self._interface

        if distro.detect().name == 'SuSE':
            conf_file = "/etc/sysconfig/network/ifcfg-%s" % self._interface

        self.bring_down()
        self._move_interfaceconfile("%s.backup" % conf_file, conf_file)

    def ping_check(self, peer_ip, count, option=None, flood=False):
        """
        Utility perform Ping operation on Peer IP address and return status

        :param peer_ip :  Peer IP address
        :param count   :  ping count
        :param option  :  Default is None
        :param flood   :  Default is False
        :return        :  True / False if ping success
        """
        cmd = "ping -I %s %s -c %s" % (self._interface, peer_ip, count)
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
        Utility Set Mtu Size to a interface and return status
        :param mtu :  mtu size that meed to be set
        :return : return True / False in case of mtu able to set
        """
        cmd = "ip link set %s mtu %s" % (self._interface, mtu)
        try:
            process.system(cmd, shell=True)
        except process.CmdError as ex:
            raise NWException("MTU size can not be set: %s" % ex)
        try:
            cmd = "ip add show %s" % self._interface
            mtuvalue = process.system_output(cmd, shell=True).decode("utf-8") \
                .split()[4]
            if mtuvalue == mtu:
                return True
        except Exception as ex:  # pylint: disable=W0703
            raise NWException("setting MTU value in host failed: %s", ex)
        return False

    def is_link_up(self):
        """
        Checks if the interface link is up
        :return: True if the interface's link up, False otherwise.
        """
        if 'up' in genio.read_file("/sys/class/net/%s/operstate" % self._interface):
            log.info("Interface %s link is up", self._interface)
            return True
        return False

    def bring_up(self):
        """
         Utility  Used to Bring up interface
        :return :  True In based on success otherwise Raise NWException
        """
        cmd = "ifup %s" % self._interface
        try:
            process.system(cmd, ignore_status=False, sudo=True)
            return True
        except process.CmdError as ex:
            raise NWException("ifup fails: %s" % ex)

    def bring_down(self):
        """
        Utility  Used to Bring down interface
        :return :  True In based on success otherwise Raise NWException
        """
        cmd = "ifdown %s" % self._interface
        try:
            process.system(cmd, sudo=True)
            return True
        except Exception as ex:
            raise NWException("ifdown fails: %s" % ex)

    def _move_interfaceconfile(self, src_conf, dest_conf):
        if os.path.exists(src_conf):
            shutil.move(src_conf, dest_conf)
        else:
            raise NWException("%s interface not available" % self._interface)

    def get_hwaddr(self):
        try:
            interface_file = open(
                '/sys/class/net/%s/address' % self._interface)
            hwaddr = interface_file.read().strip()
            interface_file.close()
            return hwaddr
        except OSError as ex:
            raise NWException("interface not found : %s" % ex)

    def set_hwaddr(self, hwaddr):
        """
        Utility which set Hw address to Interface

        :param hwaddr: Pass Hardwae address for defined interface
        """
        try:
            process.system('ifconfig %s hw ether %s' %
                           (self._interface, hwaddr))
        except Exception as ex:
            raise NWException("ifdown fails: %s" % ex)

    def add_hardware_address(self, maddr):
        """
        Utility which add mac address to a interface return Status
        :param maddr: Mac address
        :return: True /False Based on success
        """
        try:
            process.system('ip maddr add %s dev %s' % (maddr, self._interface))
            return True
        except Exception as ex:
            raise NWException("ifdown fails: %s" % ex)
        return False

    def remove_hardware_address(self, maddr):
        """
        Utility remove mac address from interface and return Status

        :param maddr: Mac address
        :return:True/False Based on success
        """
        try:
            process.system('ip maddr del %s dev %s' % (maddr, self._interface))
            return True
        except Exception as ex:
            raise NWException("ifdown fails: %s" % ex)
        return False

    def get_name(self):
        return self._interface


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
                "connection not established to peer machine: %s", ex)

    def set_mtu_peer(self, peer_interface, mtu):
        """
        Set MTU size in peer interface
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
        except Exception as ex:  # pylint: disable=W0703
            return False

    def get_peer_interface(self, peer_ip):
        """
        :param peer_ip : IP address of Peer system
        :return        : Interface name of given IP in Peer system
                         get peer interface from peer ip if
        """
        cmd = "ip addr show"
        try:
            for line in self.session.cmd(cmd).stdout.decode("utf-8") \
                                                    .splitlines():
                if peer_ip in line:
                    peer_interface = line.split()[-1]
        except Exception as ex:  # pylint: disable=W0703
            if peer_interface == "":
                return peer_interface
        else:
            return peer_interface
