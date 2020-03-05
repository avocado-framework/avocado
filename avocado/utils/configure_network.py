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
#         : Praveen K Pandey <praveen@linux.vnet.ibm.com>

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
from . import wait

log = logging.getLogger('avocado.test')


class NWException(Exception):
    """
    Base Exception Class for all exceptions
    """


class NetworkInterface:
    """
    class For network interface
    """

    def __init__(self, if_name, remote_session=None):  # pylint: disable=W0231
        self.name = if_name
        self.remote_session = remote_session

    def set_ip(self, ipaddr, netmask, interface_type=None):
        """
        utility assign a IP  address (given to this utility ) to  Interface
        and gernerate interface file based on distro
        :param ipaddr : ip address which need to configure for interface
        :param netmask: Netmask which is associated  to provided IP
        :param interface_type: Interface type IPV4 or IPV6 , default is
                               IPV4 style
        """

        if distro.detect().name == 'rhel':
            conf_file = "/etc/sysconfig/network-scripts/ifcfg-%s" % self.name
            self._move_config_file(conf_file, "%s.backup" % conf_file)
            with open(conf_file, "w") as network_conf:
                if interface_type:
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

        if distro.detect().name == 'SuSE':
            conf_file = "/etc/sysconfig/network/ifcfg-%s" % self.name
            self._move_config_file(conf_file, "%s.backup" % conf_file)
            with open(conf_file, "w") as network_conf:
                network_conf.write("IPADDR=%s \n" % ipaddr)
                network_conf.write("NETMASK='%s' \n" % netmask)
                network_conf.write("IPV6INIT=yes \n")
                network_conf.write("IPV6_AUTOCONF=yes \n")
                network_conf.write("IPV6_DEFROUTE=yes")
        self.bring_up()

    def unset_ip(self):
        """
        Utility to unassign IP to Defined Interface
        """
        if distro.detect().name == 'rhel':
            conf_file = "/etc/sysconfig/network-scripts/ifcfg-%s" % self.name

        if distro.detect().name == 'SuSE':
            conf_file = "/etc/sysconfig/network/ifcfg-%s" % self.name

        self.bring_down()
        self._move_config_file("%s.backup" % conf_file, conf_file)

    def ping_check(self, peer_ip, count, option=None, flood=False):
        """
        utility perform Ping operation on Peer IP address and return status
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

    def set_mtu(self, mtu):
        """
        utility set mtu size to a interface and return status
        :param mtu :  mtu size that meed to be set
        :ptype : String
        :return : return True / False in case of mtu able to set
        """
        cmd = "ip link set %s mtu %s" % (self.name, mtu)

        cmd_mtu = "ip add show %s" % self.name
        mtu_value = ''
        try:
            if self.remote_session:
                self.remote_session.cmd(cmd)
                mtu_value = self.remote_session.cmd(
                    cmd_mtu).stdout.decode("utf-8")
            else:
                process.system(cmd, shell=True)
                mtu_value = process.system_output(
                    cmd_mtu, shell=True).decode("utf-8")
            if mtu in mtu_value and wait.wait_for(self.is_link_up, timeout=120, args=[self.name]):
                return True
        except Exception:  # pylint: disable=W0703
            return False
        return False

    def get_link_status(self):
        if self.remote_session:
            return self.session.cmd("cat /sys/class/net/%s/operstate" % self.name).stdout.decode('utf-8')
        else:
            return genio.read_file("/sys/class/net/%s/operstate" % self.name)

    def is_link_up(self):
        """
        Checks if the interface link is up
        :return: True if the interface's link up, False otherwise.
        """
        if self.get_link_state() in ['up', 'UP']:
            return True
        else:
            return False

    def bring_up(self):
        """
        utility used to Bring up interface
        """
        cmd = "ifup %s" % self.name
        try:
            process.system(cmd, ignore_status=False, sudo=True)
            return True
        except process.CmdError as ex:
            raise NWException("ifup fails: %s" % ex)

    def bring_down(self):
        """
        Utility  Used to Bring down interface
        """
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
            interface_file = open(
                '/sys/class/net/%s/address' % self.name)
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
                           (self.name, hwaddr))
        except Exception as ex:
            raise NWException("ifdown fails: %s" % ex)

    def add_hwaddr_address(self, maddr):
        """
        Utility which add mac address to a interface return Status
        :param maddr: Mac address
        :return: True  Based on success if fail raise NWException
        """
        try:
            process.system('ip maddr add %s dev %s' % (maddr, self.name))
            return True
        except Exception as ex:
            raise NWException("ifdown fails: %s" % ex)

    def remove_hwaddr_address(self, maddr):
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


class Host:
    """
    class for peer function
    """

    def __init__(self, host, port=22, username=None,
                 key=None, password=None):
        """
        create a object for accesses remote machine
        """
        self.host = host
        self.port = port
        self.username = username
        self.key = key
        self.password = password
        self.session = None
        self.interfaces = []
        self._connect()
        self._populate_interfaces()

    def _connect(self):
        if self.host and self.port and self.username:
            try:
                self.session = Session(self.host, port=self.port, user=self.username,
                                       key=self.key, password=self.password)
            except Exception as ex:  # pylint: disable=W0703
                raise NWException(
                    "Could not connect to host: {}".format(ex))

    def is_remote(self):
        if self.session:
            return True
        else:
            return False

    def _populate_interfaces(self):
        names = []
        if self.is_remote():
            cmd = 'ls /sys/class/net'
            try:
                names = self.session.cmd(cmd).stdout.decode(
                    "utf-8").strip().split('\n')
            except Exception:  # pylint: disable=W0703
                pass
        else:
            names = os.listdir('/sys/class/net')

        for name in names:
            self.interfaces.append(NetworkInterface(
                name, remote_session=self.session))
