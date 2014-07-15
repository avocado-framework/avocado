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


class CoreGeneratorConfig(object):

    """
    Configures the system for automatic `core` file generation
    """

    def __init__(self):
        self.previous_core_soft_limit = None
        self.previous_core_hard_limit = None
        self.previous_core_pattern = None
        self.enabled = None

    def enable(self):
        """
        Runs all necessary actions to enable core files

        Together with `disable()` this is this class' primary interface
        """
        (self.previous_core_soft_limit,
         self.previous_core_hard_limit) = self.get_limits()

        self.set_limits()

    def disable(self):
        """
        Runs all necessary actions to disable core files

        Together with `enable()` this is this class' primary interface
        """
        self.set_limits(self.previous_core_soft_limit,
                        self.previous_core_hard_limit)

        (new_soft_limit,
         new_hard_limit) = self.get_limits()

        assert self.previous_core_soft_limit == new_soft_limit
        assert self.previous_core_hard_limit == new_hard_limit

    def get_limits(self):
        """
        Get the current value for generated core files size limit

        :returns: the current soft and hard limit, both as integers
        :rtype: tuple
        """
        return resource.getrlimit(resource.RLIMIT_CORE)

    def set_limits(self,
                   soft=resource.RLIM_INFINITY,
                   hard=resource.RLIM_INFINITY):
        """
        Configures the current user core file size limit
        """
        resource.setrlimit(resource.RLIMIT_CORE, (soft, hard))

    def set_core_pattern(self):
        """
        Configures the `kernel.core_pattern` system tunable

        So that core dumps are generated within a test data directory
        """
        pass


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
