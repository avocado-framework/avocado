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
# This code was inspired in the autotest project,
#
# client/base_utils.py
#
# Copyright: 2019 IBM
# Authors : Praveen K Pandey <praveen@linux.vnet.ibm.com>


"""
Linux OS  utilities
"""

import re

from . import genio


def sysctl(key, value=None):
    """Generic implementation of sysctl, to read and write.

    :param key: A location under /proc/sys
    :param value: If not None, a value to write into the sysctl.

    :return: The single-line sysctl value as a string.
    """
    path = '/proc/sys/%s' % key
    if value is not None:
        genio.write_one_line(path, str(value))
    return genio.read_one_line(path)


def sysctl_kernel(key, value=None):
    """implementation of sysctl, for kernel params"""
    if value is not None:
        # write
        genio.write_one_line('/proc/sys/kernel/%s' % key, str(value))
    else:
        # read
        out = genio.read_one_line('/proc/sys/kernel/%s' % key)
        return int(re.search(r'\d+', out).group(0))
