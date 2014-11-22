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
Module that contains runtime configuration
"""

#: Contains a list of binary names that should be run via the GNU debugger
#: and be stopped at a given point. That means that a breakpoint will be set
#: using the given expression
GDB_RUN_BINARY_NAMES_EXPR = []

#: Wether to enable the automatic generation of core dumps for applications
#: that are run inside the GNU debugger
GDB_ENABLE_CORE = False

#: Path to the GDB binary
GDB_PATH = None

#: Path to the gdbserver binary
GDBSERVER_PATH = None

#: Sometimes it's useful for the framework and API to know about the test that
#: is currently running, if one exists
CURRENT_TEST = None
