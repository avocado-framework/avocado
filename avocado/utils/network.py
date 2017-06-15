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

"""
Module with network related utility functions
"""

import socket

from .data_structures import Borg


def is_port_free(port, address):
    """
    Return True if the given port is available for use.

    :param port: Port number
    """
    try:
        s = socket.socket()
        if address == "localhost":
            s.bind((address, port))
            free = True
        else:
            s.connect((address, port))
            free = False
    except socket.error:
        if address == "localhost":
            free = False
        else:
            free = True
    s.close()
    return free


def find_free_port(start_port, end_port, address="localhost"):
    """
    Return a host free port in the range [start_port, end_port].

    :param start_port: First port that will be checked.
    :param end_port: Port immediately after the last one that will be checked.
    """
    for i in range(start_port, end_port):
        if is_port_free(i, address):
            return i
    return None


def find_free_ports(start_port, end_port, count, address="localhost"):
    """
    Return count of host free ports in the range [start_port, end_port].

    :param count: Initial number of ports known to be free in the range.
    :param start_port: First port that will be checked.
    :param end_port: Port immediately after the last one that will be checked.
    """
    ports = []
    i = start_port
    while i < end_port and count > 0:
        if is_port_free(i, address):
            ports.append(i)
            count -= 1
        i += 1
    return ports


class PortTracker(Borg):

    """
    Tracks ports used in the host machine.
    """

    def __init__(self):
        Borg.__init__(self)
        self.address = 'localhost'
        self.start_port = 5000
        if not hasattr(self, 'retained_ports'):
            self._reset_retained_ports()

    def __str__(self):
        return 'Ports tracked: %r' % self.retained_ports

    def _reset_retained_ports(self):
        self.retained_ports = []

    def register_port(self, port):
        if (port not in self.retained_ports) and is_port_free(port, self.address):
            self.retained_ports.append(port)
        else:
            raise ValueError('Port %d in use' % port)
        return port

    def find_free_port(self, start_port=None):
        if start_port is None:
            start_port = self.start_port
        port = start_port
        while ((port in self.retained_ports) or
               (not is_port_free(port, self.address))):
            port += 1
        self.retained_ports.append(port)
        return port

    def release_port(self, port):
        if port in self.retained:
            self.retained.remove(port)
