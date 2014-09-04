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

    def configure(self, parser):
        self.parser = parser
        runner = self.parser.runner
        runner.add_argument('--gdb-run-bin', action='append',
                            default=[], metavar='BINARY_PATH',
                            help=('Set a breakpoint on a given binary to be '
                                  'run inside the GNU debugger. Format should '
                                  'be "<binary>[:breakpoint]". Breakpoint '
                                  'defaults to "main"'))

        self.configured = True

    def activate(self, app_args):
        try:
            for binary in app_args.gdb_run_bin:
                runtime.GDB_RUN_BINARY_NAMES_EXPR.append(binary)
        except AttributeError:
            pass
