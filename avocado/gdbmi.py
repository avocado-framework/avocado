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
# Authors: Cleber Rosa <cleber@redhat.com>

"""
Module that provides communication with GDB via its GDB/MI interpreter
"""

from avocado.external import gdbmi_parser

GDB_PROMPT = '(gdb)'
GDB_EXIT = '^exit'
GDB_BREAK_CONTITIONS = [GDB_PROMPT, GDB_EXIT]

def parse_line(line):
    if not line.endswith('\n'):
        line = "%s\n" % line
    return gdbmi_parser.process(line)

def encode_cli_command(command):
    """
    Returns a regular GDB command

    :param command: the regular cli command to send
    """
    return '-interpreter-exec console "%s"' % command
