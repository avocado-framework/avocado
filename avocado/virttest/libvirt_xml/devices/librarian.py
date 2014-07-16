"""
Module to hide underlying device xml handler class implementation
"""

import os
from virttest.libvirt_xml import base

# Avoid accidental names like __init__, librarian, and/or other support modules
DEVICE_TYPES = ['disk', 'filesystem', 'controller', 'lease',
                'hostdev', 'redirdev', 'smartcard', 'interface', 'input',
                'hub', 'graphics', 'video', 'parallel', 'serial', 'console',
                'channel', 'sound', 'watchdog', 'memballoon', 'rng',
                'seclabel', 'address', 'emulator']


def get(name):
    """
    Returns named device xml element's handler class

    :param name: the device name
    :return: the named device xml element's handler class
    """
    mod_path = os.path.abspath(os.path.dirname(__file__))
    handler_cl = base.load_xml_module(mod_path, name, DEVICE_TYPES)
    return handler_cl
