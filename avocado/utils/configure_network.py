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
# Copyright: 2019-2020 IBM
# Copyright: 2019-2020 Red Hat Inc.
# Authors : Beraldo Leal <bleal@redhat.com>
#         : Praveen K Pandey <praveen@linux.vnet.ibm.com>
#         : Vaishnavi Bhat <vaishnavi@linux.vnet.ibm.com>

"""
Configure network when interface name and interface IP is available.
"""

import json
import logging
import os
import shutil
import time

from ipaddress import ip_interface

from . import distro
from . import process
from . import wait
from .ssh import Session


log = logging.getLogger('avocado.test')

# Probably this will be replaced by aexpect
def _run_command(command, remote_session=None, sudo=False):
    if remote_session:
        if sudo:
            command = "sudo {}".format(command)
        return remote_session.cmd(command).stdout.decode('utf-8')
    else:
        return process.system_output(command, sudo=sudo).decode('utf-8')


class NWException(Exception):
    """
    Base Exception Class for all exceptions
    """


class NetworkInterface:

    """
    NetworkInterface, Provides  API's to Perform certain
    operation on a  Network Interface
    """

    def __init__(self, if_name, if_type='Ethernet', remote_session=None):  # pylint: disable=W0231
        self.name = if_name
        self.if_type = if_type
        self.remote_session = remote_session

    def _get_interface_details(self, version=4):
        output = ''
        cmd = "ip -{} -j address show {}".format(version, self.name)
        output = _run_command(cmd, self.remote_session)
        try:
            return json.loads(output)
        except (KeyError, json.JSONDecodeError):
            msg = "Unable to get IP address on interface {}".format(self.name)
            log.error(msg)
            raise NWException(msg)

    def _move_file_to_backup(self, filename, ignore_missing=True):
        destination = "{}.backup-{}".format(filename, time.time())
        if os.path.exists(filename):
            shutil.move(filename, destination)
        else:
            if not ignore_missing:
                raise NWException("%s interface not available" % self.name)

    def _write_to_file(self, filename, values):
        self._move_file_to_backup(filename)

        with open(filename, 'w+') as fp:
            for key, value in values:
                fp.write("{}={}\n".format(key, value))

    def add_hwaddr(self, hwaddr):
        """
        Utility which add mac address to a interface return Status
        :param hwaddr: Hardware Address (Mac Address)
        :return: True  Based on success if fail raise NWException
        """
        cmd = "ip link set dev {} address {}".format(self.name, hwaddr)
        try:
            _run_command(cmd, self.remote_session, sudo=True)
        except Exception as ex:
            raise NWException("Adding hw address fails: %s" % ex)

    def add_ipaddr(self, ipaddr, netmask):
        ip = ip_interface("{}/{}".format(ipaddr, netmask))
        cmd = 'ip addr add {} dev {}'.format(ip.compressed,
                                             self.name)
        try:
            _run_command(cmd, self.remote_session, sudo=True)
        except Exception as ex:
            raise NWException("Failed to add address {}".format(ex))

    def bring_down(self):
        """Utility used to Bring down interface """

        cmd = "ifdown {}".format(self.name)
        try:
            _run_command(cmd, self.remote_session, sudo=True)
        except Exception as ex:
            raise NWException("ifdown fails: %s" % ex)

    def bring_up(self):
        """Utility used to Bring up interface"""

        cmd = "ifup {}".format(self.name)
        try:
            _run_command(cmd, self.remote_session, sudo=True)
        except Exception as ex:
            raise NWException("ifup fails: %s" % ex)

    def is_link_up(self):
        """
        Checks if the interface link is up
        :return: True if the interface's link up, False otherwise.
        """
        if self.get_link_state() in ['up', 'UP']:
            return True
        else:
            return False

    def is_remote(self):
        if self.remote_session:
            return True
        else:
            return False

    def get_ipaddrs(self, version=4):
        """Get the IP addresses from a network interface.

        Interfaces can hold multiple IP addresses. This method will return a
        list with all addresses on this interface.

        :param version: IP version number (4 or 6). This must be a integer.
        :return: IP address
        """
        if version not in [4, 6]:
            raise NWException("Version {} not supported".format(version))

        try:
            details = self._get_interface_details(version)
            addr_info = details[0].get('addr_info')
            if addr_info:
                return list(map(lambda x: x.get('local'),
                            addr_info))
        except (NWException, IndexError, KeyError) as e:
            raise NWException(e)

    def get_hwaddr(self):
        cmd = "cat /sys/class/net/{}/address".format(self.name)
        try:
            return _run_command(cmd, self.remote_session)
        except Exception as ex:
            raise NWException("Failed to get hw address: {}".format(ex))

    def get_link_state(self):
        """Method used to get the link state of an interface.

        This method will return 'up', 'down' or 'unknown', based on the network
        interface state. Or it will raise a NWException if is unabble to get
        the interface state.
        """
        cmd = "cat /sys/class/net/{}/operstate".format(self.name)
        try:
            return _run_command(cmd, self.remote_session)
        except process.CmdError as e:
            msg = ('Failed to get link state. Maybe the interface is '
                   'missing. {}'.format(e))
            raise NWException(msg)

    def get_mtu(self):
        pass

    def ping_check(self, peer_ip, options=None):
        """This method will try to ping a peer address (IPv4 or IPv6).

        You should provide a IPv4 or IPV6 that would like to ping. This
        method will try to ping the peer and if fails it will raise a
        NWException.

        :param peer_ip: Peer IP address (IPv4 or IPv6)
        :param options: ping command options. Default is None
        """
        cmd = "ping -I {} {}".format(self.name, peer_ip)
        if options is not None:
            cmd = "{} {}".format(cmd, options)
        try:
            _run_command(cmd, self.remote_session)
        except Exception as ex:
            raise NWException("Failed to ping: {}".format(ex))

    def save(self, ipaddr, netmask):
        """
        Utility assign a IP  address (given to this utility ) to  Interface
        And generate interface file in sysfs based on distribution

        :param ipaddr : ip address which need to configure for interface
        :param netmask: Netmask which is associated  to provided IP
        :param interface_type: Interface type IPV4 or IPV6 , default is
                               IPV4 style
        """
        current_distro = distro.detect()

        filename = "ifcfg-{}".format(self.name)
        if current_distro.name in ['rhel', 'fedora']:
            path = "/etc/sysconfig/network-scripts"
        elif current_distro.name == 'SuSE':
            path = "/etc/sysconfig/network"
        else:
            msg = 'Distro not supported by API. Could not save ipaddr.'
            raise NWException(msg)

        if ipaddr not in self.get_ipaddrs():
            msg = ('ipaddr not configured on interface. To avoid '
                   'inconsistency, please Set the ipaddr first.')
            raise NWException(msg)

        self._write_to_file("{}/{}".format(path, filename),
                            {'TYPE': self.if_type,
                             'BOOTPROTO': 'none',
                             'NAME': self.name,
                             'DEVICE': self.name,
                             'ONBOOT': 'yes',
                             'IPADDR': ipaddr,
                             'NETMASK': netmask,
                             'IPV6INIT': 'yes',
                             'IPV6_AUTOCONF': 'yes',
                             'IPV6_DEFROUTE': 'yes'})

    def set_hwaddr(self, hwaddr):
        """
        Utility which set Hw address to Interface
        :param hwaddr: Pass Hardwae address for defined interface
        """
        cmd = 'ip link set {} address {}'.format(self.name, hwaddr)
        try:
            self._run_command(cmd, sudo=True)
        except Exception as ex:
            raise NWException("Setting Mac address failed: %s" % ex)

    def set_mtu(self, mtu):
        """
        Utility set mtu size to a interface and return status

        :param mtu :  mtu size that meed to be set
        :ptype : String
        :return : return True / False in case of mtu able to set
        """
        cmd = "ip link set %s mtu %s" % (self.name, mtu)
        _run_command(cmd, self.remote_session, sudo=True)
        wait.wait_for(self.is_link_up, timeout=timeout)
        if mtu != self.get_mtu():
            raise NWException("Failed to set MTU.")

    def remove_ipaddr(self, ipaddr, netmask):
        """Remove an IP address from this interface.

        This method will try to remove the address from this interface
        and if fails it will raise a NWException. Be careful, you can
        lost connection.

        You must have sudo permissions to run this method on a host.
        """
        ip = ip_interface("{}/{}".format(ipaddr, netmask))
        cmd = 'ip addr del {} dev {}'.format(ip.compressed,
                                             self.name)
        try:
            _run_command(cmd, self.remote_session, sudo=True)
        except Exception as ex:
            msg = 'Failed to remove ipaddr. {}'.format(ex)
            raise NWException(msg)


class Host:
    """
    class for peer function
    """

    def __init__(self, host, port=22, username=None,
                 key=None, password=None):
        self.host = host
        self.port = port
        self.username = username
        self.key = key
        self.password = password
        self.remote_session = None

        self._connect()

    def _connect(self):
        if self.host and self.port and self.username:
            try:
                self.remote_session = Session(host=self.host,
                                              port=self.port,
                                              user=self.username,
                                              key=self.key,
                                              password=self.password)
            except Exception as ex:
                raise NWException("Could not connect to host: {}".format(ex))

    @property
    def interfaces(self):
        cmd = 'ls /sys/class/net'
        try:
            names = _run_command(cmd, self.remote_session).split()
        except Exception as ex:
            raise NWException("Failed to get interfaces: {}".format(ex))

        session = self.remote_session
        return list(map(lambda x: NetworkInterface(if_name=x,
                                                   remote_session=session),
                        names))
