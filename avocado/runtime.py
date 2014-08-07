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

#: Controls if running processes via the standard avocado APIs will run an
# application inside the GNU debugger
PROCESS_DEBUG_GDB = False

#: Contains a list of processes names that should be run via the GNU debugger
# COMM here is how a process name is usually called in procutils (ps) and
# similar system utilities. In practice, the ARGV[0] of the command line is
# going to be checked agains this list
PROCESS_DEBUG_COMM_NAMES = []
