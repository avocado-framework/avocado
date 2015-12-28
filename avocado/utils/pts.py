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
# Copyright: Red Hat Inc. 2014
# Author: Cleber Rosa <crosa@redhat.com>

"""
Functions dedicated to pseudo terminal manipulation
"""

import os
import pty
import ctypes

__all__ = ['ptsname', 'openpty']


def get_libc():
    libc_paths = ['/lib64/libc.so.6', '/lib/libc.so.6',
                  '/lib/x86_64-linux-gnu/libc.so.6']
    for lib_path in libc_paths:
        if os.path.exists(lib_path):
            return ctypes.cdll.LoadLibrary(lib_path)


def ptsname(master_fd):
    """
    Returns the name of the pts device associated with the given master file descriptor

    :param master_fd: the file descriptor of the master of the pseudo terminal
    :type master_fd: int
    :returns: the name of the pseudo terminal file
    :rtype: str
    """
    libc = get_libc()
    ptsname_ = libc.ptsname
    ptsname_.argtypes = [ctypes.c_int]
    ptsname_.restype = ctypes.c_char_p

    return ptsname_(master_fd)


def openpty():
    """
    Simple wrapper around :func:`pty.openpty` that returns the file name

    This adds the pseudo terminal file path to the extra information returned
    by the standard library.

    :returns: a tuple with the master file descriptor, slave file descriptor
              and the path of the pseudo file path
    :rtype: tuple(int, int, str)
    """
    master, slave = pty.openpty()
    path = ptsname(master)
    return (master, slave, path)
