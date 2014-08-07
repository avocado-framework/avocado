#!/usr/bin/python

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

import os

from avocado import test
from avocado import gdb
from avocado.utils import process


class gdbtest(test.Test):

    """
    Execute the gdb test
    """

    def gdb_cmd_log(self, cmd):
        """
        Sends a GDB command and logs it
        """
        self.log.debug("[GDB] sending command: %s", cmd)
        return self.gdb.cmd(cmd)

    def setup(self):
        self.gdb = gdb.GDB()

        # Compile return99 binary
        self.return99_binary_path = os.path.join(self.outputdir, 'return99')
        return99_source_path = self.get_data_path('return99.c')
        process.system('gcc -g %s -o %s' % (return99_source_path,
                                            self.return99_binary_path))

        # Compile segfault binary
        self.segfault_binary_path = os.path.join(self.outputdir, 'segfault')
        segfault_source_path = self.get_data_path('segfault.c')
        process.system('gcc -g %s -o %s' % (segfault_source_path,
                                            self.segfault_binary_path))

    def action(self):
        """
        Execute test
        """

        # The following commands should exist in any standard GDB,
        # that is, should not depend on optionally compiled features
        existing_cmds = ["-list-target-features",
                         "-break-info",
                         "-break-list",
                         "-thread-info",
                         "-stack-info-frame",
                         "-stack-info-depth"]

        self.log.info("Testing valid GDB commands")
        for cmd in existing_cmds:
            info_cmd = "-info-gdb-mi-command %s" % cmd[1:]
            r = self.gdb_cmd_log(info_cmd)
            self.assertEqual(r.result.command.exists, 'true')
            self.gdb.cmd(cmd)

        # following commands are obviously *not* valid
        non_existing_cmds = ["-foobar",
                             "-magic8ball",
                             "-find-me-the-bug",
                             "-auto-debug-it"]
        self.log.info("Testing GDB commands that do not exist")
        for cmd in non_existing_cmds:
            info_cmd = "-info-gdb-mi-command %s" % cmd[1:]
            r = self.gdb_cmd_log(info_cmd)
            self.assertEqual(r.result.command.exists, 'false')

        # load a file and check the results
        self.log.info("Testing that GDB loads a file and sets a breakpoint")
        file_cmd = "-file-exec-and-symbols %s" % self.return99_binary_path
        r = self.gdb_cmd_log(file_cmd)
        self.assertEqual(r.class_, 'done')
        break_cmd = "-break-insert 5"
        r = self.gdb_cmd_log(break_cmd)
        self.assertEqual(r.class_, 'done')
        self.assertEqual(r.result.bkpt.number, '1')
        self.assertEqual(r.result.bkpt.enabled, 'y')
        break_del_cmd = "-break-delete 1"
        r = self.gdb_cmd_log(break_del_cmd)
        self.assertEqual(r.class_, 'done')

        # run the binary
        self.log.info("Testing that GDB execs the file")
        run_cmd = "-exec-run"
        r = self.gdb_cmd_log(run_cmd)
        self.assertEqual(r.class_, 'running')

        # Terminate GDB gracefully
        self.log.info("Testing that GDB exists cleanly")
        self.gdb_cmd_log("-gdb-exit")
        self.assertEqual(self.gdb.process.wait(), 0)

        # Start a new GDB, to load another file
        self.gdb = gdb.GDB()

        # load a file and check the results
        self.log.info("Testing that responds to received signals")
        file_cmd = "-file-exec-and-symbols %s" % self.segfault_binary_path
        r = self.gdb_cmd_log(file_cmd)
        self.assertEqual(r.class_, 'done')
        run_cmd = "-exec-run"
        r = self.gdb_cmd_log(run_cmd)
        self.assertEqual(r.class_, 'running')

        other_messages = self.gdb.read_until_break()
        for msg in other_messages:

            parsed_msg = gdb.parse_mi(msg)
            if ((parsed_msg.class_ == 'stopped') and
                    (parsed_msg.result.signal_name == 'SIGSEGV')):

                core_path = "%s.core" % self.segfault_binary_path
                gcore_cmd = 'gcore %s' % core_path
                gcore_cmd = gdb.encode_mi_cli(gcore_cmd)
                r = self.gdb_cmd_log(gcore_cmd)
                self.assertEqual(r.class_, 'done')
