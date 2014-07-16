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

import fcntl
import re
import socket
import struct

from avocado.utils import process
from avocado.linux import arch

import logging

log = logging.getLogger('avocado.test')


class NetError(Exception):
    pass


def local_runner(cmd, timeout=None):
    return process.run(cmd, verbose=False, timeout=timeout).stdout


def local_runner_status(cmd, timeout=None):
    return process.run(cmd, verbose=False, timeout=timeout).exit_status


def is_port_free(port, address):
    """
    Return True if the given port is available for use.

    :param port: Port number
    """
    try:
        s = socket.socket()
        #s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if address == "localhost":
            s.bind(("localhost", port))
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


def get_ip_address_by_interface(ifname):
    """
    returns ip address by interface
    :param ifname - interface name
    :raise NetError - When failed to fetch IP address (ioctl raised IOError.).

    Retrieves interface address from socket fd trough ioctl call
    and transforms it into string from 32-bit packed binary
    by using socket.inet_ntoa().

    """
    mysocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        return socket.inet_ntoa(fcntl.ioctl(
            mysocket.fileno(),
            arch.SIOCGIFADDR,
            # ifname to binary IFNAMSIZ == 16
            struct.pack('256s', ifname[:15])
        )[20:24])
    except IOError:
        raise NetError(
            "Error while retrieving IP address from interface %s." % ifname)


def get_host_ip_address(params):
    """
    returns ip address of host specified in host_ip_addr parameter If provided
    otherwise ip address on interface specified in netdst parameter is returned
    :param params
    """
    host_ip = params.get('host_ip_addr', None)
    if not host_ip:
        host_ip = get_ip_address_by_interface(params.get('netdst'))
        log.warning("No IP address of host was provided, using IP address"
                    " on %s interface", str(params.get('netdst')))
    return host_ip


def convert_ipv4_to_ipv6(ipv4):
    """
    Translates a passed in string of an ipv4 address to an ipv6 address.

    :param ipv4: a string of an ipv4 address
    """

    converted_ip = "::ffff:"
    split_ipaddress = ipv4.split('.')
    try:
        socket.inet_aton(ipv4)
    except socket.error:
        raise ValueError("ipv4 to be converted is invalid")
    if (len(split_ipaddress) != 4):
        raise ValueError("ipv4 address is not in dotted quad format")

    for index, string in enumerate(split_ipaddress):
        if index != 1:
            test = str(hex(int(string)).split('x')[1])
            if len(test) == 1:
                final = "0"
                final += test
                test = final
        else:
            test = str(hex(int(string)).split('x')[1])
            if len(test) == 1:
                final = "0"
                final += test + ":"
                test = final
            else:
                test += ":"
        converted_ip += test
    return converted_ip


def get_net_if(runner=None, state=None):
    """
    :param runner: command runner.
    :param div_phy_virt: if set true, will return a tuple division real
                         physical interface and virtual interface
    :return: List of network interfaces.
    """
    if runner is None:
        runner = local_runner
    if state is None:
        state = ".*"
    cmd = "ip link"
    result = runner(cmd)
    return re.findall(r"^\d+: (\S+?)[@:].*state %s.*$" % (state),
                      result,
                      re.MULTILINE)


def get_net_if_addrs(if_name, runner=None):
    """
    Get network device ip addresses. ioctl not used because it's not
    compatible with ipv6 address.

    :param if_name: Name of interface.
    :return: List ip addresses of network interface.
    """
    if runner is None:
        runner = local_runner
    cmd = "ip addr show %s" % (if_name)
    result = runner(cmd)
    return {"ipv4": re.findall("inet (.+?)/..?", result, re.MULTILINE),
            "ipv6": re.findall("inet6 (.+?)/...?", result, re.MULTILINE),
            "mac": re.findall("link/ether (.+?) ", result, re.MULTILINE)}
