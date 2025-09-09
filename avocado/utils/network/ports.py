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
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""Module with network related utility functions."""

import random
import socket
import warnings

from avocado.utils.data_structures import Borg

#: Families taken into account in this class
FAMILIES = (socket.AF_INET, socket.AF_INET6)
#: Protocols taken into account in this class
PROTOCOLS = (socket.SOCK_STREAM, socket.SOCK_DGRAM)


def is_port_available(
    port, address, family=socket.AF_INET, protocol=socket.SOCK_STREAM
):
    """Return True if the given port is available for use.

    :param port: Port value to check.
    :type port: int
    :param address: Address to use this port.
    :type address: str
    :param family: Default is socket.AF_INET. Accepted values are:
                   socket.AF_INET or socket.AF_INET6.
    :type family: socket.AddressFamily.AF_*
    :param protocol: Protocol type. Default is socket.SOCK_STREAM (TCP).
                     Accepted values are: socket.SOCK_STREAM or
                     socket.SOCK_DGRAM.
    :type protocol: socket.AddressFamily.SOCK_*
    :return: True if the port is available, False otherwise.
    :rtype: bool
    """
    try:
        with socket.socket(family, protocol) as sock:
            sock.bind((address, port))
    except PermissionError:
        # Permission denied, can't be sure
        return False
    except OSError:
        # Address already in use or cannot assign requested address
        return False
    return True


def is_port_free(port, address):
    """This method is deprecated. Please use is_port_available().

    :param port: Port value to check.
    :type port: int
    :param address: Address to use this port.
    :type address: str
    :return: True if the port is available, False otherwise.
    :rtype: bool
    """

    warnings.warn("deprecated, use is_port_available() instead.", DeprecationWarning)
    return is_port_available(port, address)


# pylint: disable=R0913
def find_free_port(
    start_port=1024,
    end_port=65535,
    address="localhost",
    sequent=False,
    family=socket.AF_INET,
    protocol=socket.SOCK_STREAM,
):
    """Return a host free port in the range [start_port, end_port].

    :param start_port: header of candidate port range, defaults to 1024
    :type start_port: int
    :param end_port: ender of candidate port range, defaults to 65535
    :type end_port: int
    :param address: Socket address to bind or connect
    :type address: str
    :param sequent: Find port sequentially, random order if it's False
    :type sequent: bool
    :param family: Default is socket.AF_INET. Accepted values are:
                   socket.AF_INET or socket.AF_INET6.
    :type family: socket.AddressFamily.AF_*
    :param protocol: Protocol type. Default is socket.SOCK_STREAM (TCP).
                     Accepted values are: socket.SOCK_STREAM or
                     socket.SOCK_DGRAM.
    :type protocol: socket.AddressFamily.SOCK_*
    :return: A free port number, or None if no free port is found.
    :rtype: int or None if no free port found
    """
    ports = find_free_ports(start_port, end_port, 1, address, sequent, family, protocol)
    if ports:
        return ports[0]
    return None


# pylint: disable=R0913
def find_free_ports(
    start_port,
    end_port,
    count,
    address="localhost",
    sequent=False,
    family=socket.AF_INET,
    protocol=socket.SOCK_STREAM,
):
    """Return a number of host free ports in the range [start_port, end_port].

    :param start_port: header of candidate port range
    :type start_port: int
    :param end_port: ender of candidate port range
    :type end_port: int
    :param count: Initial number of ports known to be free in the range.
    :type count: int
    :param address: Socket address to bind or connect
    :type address: str
    :param sequent: Find port sequentially, random order if it's False
    :type sequent: bool
    :param family: Default is socket.AF_INET. Accepted values are:
                   socket.AF_INET or socket.AF_INET6.
    :type family: socket.AddressFamily.AF_*
    :param protocol: Protocol type. Default is socket.SOCK_STREAM (TCP).
                     Accepted values are: socket.SOCK_STREAM or
                     socket.SOCK_DGRAM.
    :type protocol: socket.AddressFamily.SOCK_*
    :return: A list of free port numbers.
    :rtype: list[int]
    """
    ports = []

    port_range = list(range(start_port, end_port))
    if not sequent:
        random.shuffle(port_range)
    for i in port_range:
        if is_port_available(i, address, family, protocol):
            ports.append(i)
        if len(ports) >= count:
            break

    return ports


class PortTracker(Borg):
    """Tracks ports used in the host machine."""

    def __init__(self):
        """Initializes the PortTracker instance."""
        Borg.__init__(self)
        self.address = "localhost"
        self.start_port = 5000
        if not hasattr(self, "retained_ports"):
            self._reset_retained_ports()

    def __str__(self):
        """Returns a string representation of the tracked ports.

        :return: A string showing the list of retained ports.
        :rtype: str
        """
        return f"Ports tracked: {self.retained_ports!r}"

    def _reset_retained_ports(self):
        """Resets the list of retained ports to an empty list."""
        self.retained_ports = []

    def register_port(self, port):
        """Registers a port as being in use.

        :param port: The port number to register.
        :type port: int
        :return: The registered port number if successful.
        :rtype: int
        :raises ValueError: If the port is already in use or cannot be
                             registered.
        """
        if (port not in self.retained_ports) and is_port_free(port, self.address):
            self.retained_ports.append(port)
        else:
            raise ValueError(f"Port {int(port)} in use")
        return port

    def find_free_port(self, start_port=None):
        """Finds and registers a free port.

        It starts searching from `start_port` if provided, otherwise it uses
        the default `self.start_port`.

        :param start_port: The port number to start searching from.
        :type start_port: int or None
        :return: The first free port number found.
        :rtype: int
        """
        if start_port is None:
            start_port = self.start_port
        port = start_port
        while (port in self.retained_ports) or (not is_port_free(port, self.address)):
            port += 1
        self.retained_ports.append(port)
        return port

    def release_port(self, port):
        """Releases a previously registered port.

        :param port: The port number to release.
        :type port: int
        """
        if port in self.retained_ports:
            self.retained_ports.remove(port)


# pylint: disable=wrong-import-position
from avocado.utils.deprecation import log_deprecation

log_deprecation.warning("network.ports")
