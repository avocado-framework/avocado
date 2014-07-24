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
# Author: Cleber Rosa <cleber@redhat.com>

"""Run tests with GDB goodies enabled."""

from avocado import runtime
from avocado.plugins import plugin


class GDB(plugin.Plugin):

    """
    Run tests with GDB goodies enabled
    """

    name = 'gdb'
    enabled = True

    def configure(self, app_parser, cmd_parser):
        self.parser = app_parser
        app_parser.add_argument('--gdb', action='store_true', default=False,
                                help='Run tests with GDB goodies enabled')
        app_parser.add_argument('--gdb-command', action='append', default=[],
                                help=('Include a given application to be run '
                                      'inside the GNU debugger'))
        self.configured = True

    def activate(self, app_args):
        if app_args.gdb:
            runtime.PROCESS_DEBUG_GDB = True

        for command in app_args.gdb_command:
            runtime.PROCESS_DEBUG_COMM_NAMES.append(command)
