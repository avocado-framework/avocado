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

from ..ssh import Session

from .common import _run_command
from .interfaces import NetworkInterface
from .exceptions import NWException


class Host:
    """
    This class represents a Host.

    A host can be local or remote. If you pass port, username, key or password,
    a connection will attempt to be created.

    During the initialization, all interfaces will be detected and available
    via `interfaces` attribute.

    So, for instance you could have a local and a remote host::

        local = Host(host='foo', port=22, username='foo', password='bar')
        remote = Host(host='bar')

    You can iterate over the network interfaces of any host::

        for i in remote.interfaces:
            print(i.name, i.is_link_up())
    """

    def __init__(self, host, port=22, username=None,
                 key=None, password=None):
        self.host = host
        self.port = port
        self.username = username
        self.key = key
        self.password = password
        self.remote_session = self._connect()

    def _connect(self):
        if self.username:
            session = Session(host=self.host,
                              port=self.port,
                              user=self.username,
                              key=self.key,
                              password=self.password)
            if session.connect():
                return session
            msg = "Failed connecting {}:{}".format(self.host,
                                                   self.port)
            raise NWException(msg)

    @property
    def interfaces(self):
        cmd = 'ls /sys/class/net'
        try:
            names = _run_command(cmd, self.remote_session).split()
        except Exception as ex:
            raise NWException("Failed to get interfaces: {}".format(ex))

        session = self.remote_session
        return [NetworkInterface(if_name=name,
                                 remote_session=session) for name in names]

    def get_interface_by_ipaddr(self, ipaddr):
        """Return an interface that has a specific ipaddr."""
        for interface in self.interfaces:
            if ipaddr in interface.get_ipaddrs():
                return interface
