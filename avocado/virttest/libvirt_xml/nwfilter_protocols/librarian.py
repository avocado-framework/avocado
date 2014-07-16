"""
Module to hide underlying filter protocol xml handler class implementation
"""

import os
from virttest.libvirt_xml import base

# Avoid accidental names like __init__, librarian, and/or other support modules
FILTER_TYPES = ['mac', 'vlan', 'stp', 'arp', 'rarp', 'ip', 'ipv6',
                'tcp', 'udp', 'sctp', 'icmp', 'igmp', 'esp', 'ah',
                'udplite', 'all', 'tcp_ipv6', 'udp_ipv6', 'sctp_ipv6',
                'icmpv6', 'esp_ipv6', 'ah_ipv6', 'udplite_ipv6', 'all_ipv6']


def get(name):
    """
    Returns named filter protocol xml element's handler class

    :param name: the filter protocol name
    :return: named filter protocol xml element's handler class
    """
    mod_path = os.path.abspath(os.path.dirname(__file__))
    handler_cl = base.load_xml_module(mod_path, name, FILTER_TYPES)
    return handler_cl
