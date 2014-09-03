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
