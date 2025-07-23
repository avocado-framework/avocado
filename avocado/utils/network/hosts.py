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

"""Provides a high-level API for interacting with network hosts.

This module offers classes to represent and manage local and remote hosts,
allowing users to query network interface information, validate MAC addresses,
and retrieve routing details. It abstracts the underlying command execution
for common network-related tasks.
"""

import json
import re

from avocado.utils.network.common import run_command
from avocado.utils.network.exceptions import NWException
from avocado.utils.network.interfaces import NetworkInterface
from avocado.utils.ssh import Session


class Host:
    """This class represents a base Host and shouldn't be instantiated directly.

    Use one of the child classes (LocalHost or RemoteHost).

    During the initialization of a child, network interfaces can be detected
    and made available via the `interfaces` attribute. This attribute can be
    accessed on both LocalHost and RemoteHost instances.

    So, for instance, you could have a local and a remote host::

        remote = RemoteHost(host='foo', port=22,
                            username='foo', password='bar')
        local = LocalHost()

    You can iterate over the network interfaces of any host::

        for i in remote.interfaces:
            print(f"Interface: {i.name}, Link Up: {i.is_link_up()}")
    """

    def __init__(self, host):
        """Initializes the base Host class.

        This constructor is intended to be called by sub-classes.
        Direct initialization of `Host` will raise a TypeError.

        :param host: The hostname or IP address of the host.
                    For `LocalHost`, this typically defaults to 'localhost'.
        :type host: str
        :raises TypeError: If the `Host` class is instantiated directly.
        """
        if type(self) == Host:  # pylint: disable=C0123
            raise TypeError("Host class should not be instantiated")
        self.host = host

    @property
    def interfaces(self):
        """Retrieves the network interfaces for the host.

        Detects network interface names by listing contents of '/sys/class/net'.
        Excludes 'bonding_masters' from the list.

        :return: A list of NetworkInterface objects for all network interfaces on the host.
        :rtype: list[NetworkInterface]
        :raises avocado.utils.network.exceptions.NWException: If the command to list interfaces fails or the output
                            cannot be processed.
        """
        cmd = "ls /sys/class/net"
        try:
            names = run_command(cmd, self).split()
        except Exception as ex:
            raise NWException(f"Failed to get interfaces on {self.host}: {ex}") from ex

        if "bonding_masters" in names:
            names.remove("bonding_masters")

        return [NetworkInterface(if_name=name, host=self) for name in names]

    def get_interface_by_ipaddr(self, ipaddr):
        """Retrieves a network interface that has a specific IP address.

        :param ipaddr: The IP address to search for among the host's
                       network interfaces.
        :type ipaddr: str
        :return: The NetworkInterface object matching the
                 given IP address, or None if no interface
                 is found with that IP.
        :rtype: NetworkInterface or None
        """
        for interface in self.interfaces:
            if ipaddr in interface.get_ipaddrs():
                return interface
        return None

    def get_interface_by_hwaddr(self, mac):
        """Retrieves a network interface that has a specific MAC address.

        :param mac: The MAC address to search for.
                    The MAC address format should be consistent with
                    the output of `interface.get_hwaddr()`.
        :type mac: str
        :return: The NetworkInterface object matching the
                 given MAC address, or None if no interface
                 is found with that MAC address.
        :rtype: NetworkInterface or None
        """
        for interface in self.interfaces:
            if mac in interface.get_hwaddr():
                return interface
        return None

    def get_all_hwaddr(self):
        """Gets a list of all MAC addresses on the host.

        Executes 'ip -j address' and parses the JSON output to extract
        MAC addresses.

        :return: A list of strings, where each string is a MAC address
                  found on the host.
        :rtype: list[str]
        :raises avocado.utils.network.exceptions.NWException: If the command execution fails or the JSON output
                            cannot be parsed.
        """
        cmd = "ip -j address"
        output = run_command(cmd, self)
        try:
            result = json.loads(output)
            return [str(item["address"]) for item in result]
        except Exception as ex:
            raise NWException(
                f"Could not get MAC addresses from {self.host}: {ex}"
            ) from ex

    @staticmethod
    def validate_mac_addr(mac_id):
        """Checks if a given MAC address string is in a valid format.

        A valid MAC address is defined as a 12-digit hexadecimal number,
        with pairs of digits separated by colons (e.g., '36:84:37:5a:ea:02').

        :param mac_id: The MAC address string to validate.
        :type mac_id: str or None
        :return: True if `mac_id` is a valid MAC address string, False otherwise.
                 Also returns False if `mac_id` is None.
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
        """Gets the name(s) of the interface(s) used for the default route.

        Executes 'ip -j route list default' and parses the JSON output
        to extract the device name(s) associated with the default route(s).

        :return: A list of strings, where each string is the name of an
                 interface used for a default route. Can be empty if no
                 default route is found or if the 'dev' field is missing.
        :rtype: list
        :raises avocado.utils.network.exceptions.NWException: If the command execution fails or the JSON output
                             cannot be parsed.
        """
        cmd = "ip -j route list default"
        output = run_command(cmd, self)
        try:
            result = json.loads(output)
            return [str(item["dev"]) for item in result]
        except Exception as ex:
            raise NWException(
                f"Could not get default route interface name from {self.host}: {ex}"
            ) from ex


class LocalHost(Host):
    """Represents the local machine, inheriting from `Host`.

    Use this class to get information about the network configuration
    of the machine where the script is running.

    Example::

        local = LocalHost()
        print(f"Local hostname: {local.host}")
        for iface in local.interfaces:
            print(f"Interface: {iface.name}")
    """

    def __init__(self, host="localhost"):
        """Initializes a LocalHost instance.

        :param str host: The name to assign to the local host.
                         Defaults to "localhost".
        """
        super().__init__(host)


class RemoteHost(Host):
    """Represents a remote machine, inheriting from `Host`.

    This class manages an SSH connection to a remote host to execute commands
    and retrieve network information. It requires credentials (username and
    either password or SSH key) to establish the connection.

    The class can be used as a context manager to ensure the SSH session
    is properly closed.

    Example with password::

        remote_details = {
            'host': '192.168.0.1',
            'port': 22,
            'username': 'user',
            'password': 'secure-password'
        }
        with RemoteHost(**remote_details) as remote:
            print(f"Remote interfaces on {remote.host}:")
            for iface in remote.interfaces:
                print(f"- {iface.name}")

    Example with SSH key::

        remote_key_details = {
            'host': 'server.example.com',
            'username': 'admin',
            'key': '/path/to/private/key'
        }
        with RemoteHost(**remote_key_details) as remote_server:
            # ... interact with remote_server ...
            pass # Session closes automatically on exit
    """

    # pylint: disable=R0913
    def __init__(self, host, username, port=22, key=None, password=None):
        """Initializes a RemoteHost instance and establishes an SSH connection.

        :param host: The hostname or IP address of the remote host.
        :type host: str
        :param username: The username for SSH authentication.
        :type username: str
        :param port: The SSH port on the remote host. Defaults to 22.
        :type port: int
        :param key: The file path to the private SSH key for
                        key-based authentication. Defaults to None.
        :type key: str
        :param str password: The password for password-based
                             authentication. Defaults to None.
        :raises avocado.utils.network.exceptions.NWException: If the SSH connection to the remote host fails.
        """
        super().__init__(host)
        self.port = port
        self.username = username
        self.key = key
        self.password = password
        self.remote_session = self._connect()

    def __enter__(self):
        """Enters the runtime context related to this object.

        Ensures the SSH session is active. If the session was previously
        closed or not established, it attempts to reconnect.

        :return: The instance itself.
        :rtype: RemoteHost
        """
        if not self.remote_session:
            self._connect()
        return self

    def __exit__(self, _type, _exc_value, _traceback):
        """Exits the runtime context, ensuring the SSH session is closed.

        :param _type: The exception type if an exception was raised in the
                      `with` block.
        :param _exc_value: The exception value if an exception was raised.
        :param _traceback: The traceback object if an exception was raised.
        """
        if self.remote_session:
            self.remote_session.quit()

    def _connect(self):
        """Establishes an SSH session to the remote host.

        Uses the host, port, username, and key/password provided during
        initialization.

        :return: The established SSH session object.
        :rtype: avocado.utils.ssh.Session
        :raises avocado.utils.network.exceptions.NWException: If the SSH connection attempt fails.
        """
        session = Session(
            host=self.host,
            port=self.port,
            user=self.username,
            key=self.key,
            password=self.password,
        )
        if session.connect():
            return session
        msg = (
            f"Failed connecting to {self.username}@{self.host}:{self.port}. "
            f"Ensure credentials are correct and host is reachable."
        )
        raise NWException(msg)
