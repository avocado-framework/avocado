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
import time
import fcntl
import subprocess

from avocado import test
from avocado import gdbmi


class gdbmitest(test.Test):

    GDB_ARGS = ['/usr/bin/gdb',
                '--interpreter=mi',
                '--quiet']

    """
    Execute the gdbmi test
    """

    def setup(self):
        self.gdb = subprocess.Popen(self.GDB_ARGS,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    close_fds=True)
        fcntl.fcntl(self.gdb.stdout.fileno(),
                    fcntl.F_SETFL, os.O_NONBLOCK)
        self.read_until_break()

    def action(self):
        """
        Execute test
        """
        existing_cmds = ["-list-target-features",
                         "-break-info",
                         "-break-list",
                         "-thread-info",
                         "-stack-info-frame",
                         "-stack-info-depth"]

        for cmd in existing_cmds:
            r = self.cmd("-info-gdb-mi-command %s" % cmd[1:])
            assert r.result.command.exists == 'true'
            self.cmd(cmd)
        
        r = self.cmd("-info-gdb-mi-command %s" % "foobar")
        assert r.result.command.exists == 'false'

        self.cmd("-gdb-exit")

    def cmd(self, command, log=False):
        """
        Sends a command and reads all lines until prompt

        Then parse every line received and log the result
        """
        self.send_gdb_command(command)
        response = self.read_until_break()
        for line in response:
            r = gdbmi.parse_line(line)
            if log:
                self.log.debug("[GDB] response type: %s", r.record_type)
                self.log.debug("[GDB] result: %s", r.result)
            return r

    def send_gdb_command(self, command):
        self.log.debug('[GDB] command: "%s"', command)
        command = "%s\n" % command
        self.gdb.stdin.write(command)

    def read_until_break(self, max_lines=100):
        result = []
        while True:
            line = self.read_gdb_response()
            if line in gdbmi.GDB_BREAK_CONTITIONS:
                break
            if len(result) >= max_lines:
                break
            result.append(line)
        return result

    def read_gdb_response(self, timeout=0.01, max_tries=100):
        current_try = 0
        while current_try < max_tries:
            try:
                line = self.gdb.stdout.readline()
                line = line.strip()
                if line:
                    self.log.debug('[GDB] response: "%s"', line)
                    return line
            except IOError:
                current_try += 1

            if current_try >= max_tries:
                raise ValueError("Could not read GDB response")
            else:
                time.sleep(timeout)
