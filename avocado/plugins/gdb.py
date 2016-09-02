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

from avocado.core import exceptions
from avocado.core.plugin_interfaces import CLI
from avocado.core.settings import settings
from avocado.utils import gdb
from avocado.utils import process
from avocado.utils import path as utils_path


class GDB(CLI):

    """
    Run tests with GDB goodies enabled
    """

    name = 'gdb'
    description = "GDB options for the 'run' subcommand"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        gdb_grp = run_subcommand_parser.add_argument_group('GNU Debugger support')
        gdb_grp.add_argument('--gdb-run-bin', action='append',
                             default=[], metavar='EXECUTABLE[:BREAKPOINT]',
                             help=('Run a given executable inside the GNU '
                                   'debugger, pausing at a given breakpoint '
                                   '(defaults to "main")'))

        # Because of a bug in Python's argparse, it's not possible to mark
        # this option metavar as [EXECUTABLE:]COMMANDS, signalling that the
        # EXECUTABLE is optional. https://bugs.python.org/issue11874
        gdb_grp.add_argument('--gdb-prerun-commands', action='append',
                             default=[], metavar='EXECUTABLE:COMMANDS',
                             help=('After loading an executable in GDB, '
                                   'but before actually running it, execute '
                                   'the GDB commands in the given file. '
                                   'EXECUTABLE is optional, if omitted '
                                   'COMMANDS will apply to all executables'))

        gdb_grp.add_argument('--gdb-coredump', choices=('on', 'off'),
                             default='off',
                             help=('Automatically generate a core dump when the'
                                   ' inferior process received a fatal signal '
                                   'such as SIGSEGV or SIGABRT'))

    def run(self, args):
        if 'gdb_run_bin' in args:
            for binary in args.gdb_run_bin:
                gdb.GDB_RUN_BINARY_NAMES_EXPR.append(binary)

        if 'gdb_prerun_commands' in args:
            for commands in args.gdb_prerun_commands:
                if ':' in commands:
                    binary, commands_path = commands.split(':', 1)
                    gdb.GDB_PRERUN_COMMANDS['binary'] = commands_path
                else:
                    gdb.GDB_PRERUN_COMMANDS[''] = commands

        if 'gdb_coredump' in args:
            gdb.GDB_ENABLE_CORE = True if args.gdb_coredump == 'on' else False

        system_gdb_path = utils_path.find_command('gdb', '/usr/bin/gdb')
        gdb.GDB_PATH = settings.get_value('gdb.paths', 'gdb', key_type='path',
                                          default=system_gdb_path)
        system_gdbserver_path = utils_path.find_command('gdbserver',
                                                        '/usr/bin/gdbserver')
        gdb.GDBSERVER_PATH = settings.get_value('gdb.paths',
                                                'gdbserver',
                                                key_type='path',
                                                default=system_gdbserver_path)
        process.UNDEFINED_BEHAVIOR_EXCEPTION = exceptions.TestError
