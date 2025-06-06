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
# Copyright: 2019-2020 Red Hat Inc.
# Authors : Beraldo Leal <bleal@redhat.com>

"""
This module provides an useful API for hosts in a network.
"""

import json
import re

from avocado.utils.network.common import run_command
from avocado.utils.network.exceptions import NWException
from avocado.utils.network.interfaces import NetworkInterface
from avocado.utils.ssh import Session


class Host:
    """This class represents a base Host and shouldn't be instantiated.

    Use one of the child classes (LocalHost or RemoteHost).

    During the initialization of a child, all interfaces will be detected and
    available via `interfaces` attribute. This could be accessed on LocalHost
    and RemoteHost instances.

    So, for instance, you could have a local and a remote host::

        remote = RemoteHost(host='foo', port=22,
                            username='foo', password='bar')
        local = LocalHost()

    You can iterate over the network interfaces of any host::

        for i in remote.interfaces:
            print(i.name, i.is_link_up())
    """

    def __init__(self, host):
        if type(self) == Host:  # pylint: disable=C0123
            raise TypeError("Host class should not be instantiated")
        self.host = host

    @property
    def interfaces(self):
        cmd = "ls /sys/class/net"
        try:
            names = run_command(cmd, self).split()
        except Exception as ex:
            raise NWException(f"Failed to get interfaces: {ex}") from ex

        if "bonding_masters" in names:
            names.remove("bonding_masters")

        return [NetworkInterface(if_name=name, host=self) for name in names]

    def get_interface_by_ipaddr(self, ipaddr):
        """Return an interface that has a specific ipaddr."""
        for interface in self.interfaces:
            if ipaddr in interface.get_ipaddrs():
                return interface
        return None

    def get_interface_by_hwaddr(self, mac):
        """Return an interface that has a specific mac."""
        for interface in self.interfaces:
            if mac in interface.get_hwaddr():
                return interface
        return None

    def get_all_hwaddr(self):
        """Get a list of all mac address in the host

        :return: list of mac addresses
        """
        cmd = "ip -j address"
        output = run_command(cmd, self)
        try:
            result = json.loads(output)
            return [str(item["address"]) for item in result]
        except Exception as ex:
            raise NWException(f"could not get mac addresses:" f" {ex}") from ex

    @staticmethod
    def validate_mac_addr(mac_id):
        """Check if mac address is valid.
        This method checks if the mac address is 12 digit hexadecimal number.

        Valid:
            36:84:37:5a:ea:02

        Invalid:
            36:84:37-5a-ea-02
            36-84-37-5a-ea-02
            36.84.37.5a.ea
            36:84:37:5a:ea:0ff
            2345:84:37:5a:ea:0
            3684375aea02

        :param mac_id: Network mac address
        :type pattern: str
        :return: True if a user provided a valid mac address else False
        :rtype: bool
        """

        exp = "^[0-9a-f]{2}([:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$"
        check = re.compile(exp)
        if mac_id is None:
            return False
        if re.search(check, mac_id):
            return True
        return False

    def get_default_route_interface(self):
        """Get a list of default routes interfaces

        :return: list of interface names
        """
        cmd = "ip -j route list default"
        output = run_command(cmd, self)
        try:
            result = json.loads(output)
            return [str(item["dev"]) for item in result]
        except Exception as ex:
            raise NWException(
                f"could not get default route interface name:" f" {ex}"
            ) from ex


class LocalHost(Host):
    """
    This class represents a local host and inherit from `Host`.

    You should use this class when trying to get information about your
    localhost.

    Example:

        local = LocalHost()
    """

    def __init__(self, host="localhost"):
        super().__init__(host)


class RemoteHost(Host):
    """
    This class represents a remote host and inherit from `Host`.

    You must provide at least an username to establish a connection.

    Example with password:

        remote = RemoteHost(host='192.168.0.1',
                            port=22,
                            username='foo',
                            password='bar')

    You can also provide a key instead of a password.
    """

    # pylint: disable=R0913
    def __init__(self, host, username, port=22, key=None, password=None):
        super().__init__(host)
        self.port = port
        self.username = username
        self.key = key
        self.password = password
        self.remote_session = self._connect()

    def __enter__(self):
        if not self.remote_session:
            self._connect()
        return self

    def __exit__(self, _type, _exc_value, _traceback):
        if self.remote_session:
            self.remote_session.quit()

    def _connect(self):
        session = Session(
            host=self.host,
            port=self.port,
            user=self.username,
            key=self.key,
            password=self.password,
        )
        if session.connect():
            return session
        msg = f"Failed connecting {self.host}:{self.port}"
        raise NWException(msg)
