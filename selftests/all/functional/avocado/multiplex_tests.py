#!/usr/bin/env python

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
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

import unittest
import os
import sys
import tempfile

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import process

timeout_multiplex = """
variants:
    - sleeptest:
        sleep_length = 5
        sleep_length_type = float
        timeout = 3
        timeout_type = float
"""


class MultiplexTests(unittest.TestCase):

    def run_and_check(self, cmd_line, expected_rc):
        os.chdir(basedir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))

    def test_mplex_plugin(self):
        cmd_line = './scripts/avocado multiplex tests/sleeptest/sleeptest.mplx'
        expected_rc = 0
        self.run_and_check(cmd_line, expected_rc)

    def test_mplex_plugin_nonexistent(self):
        cmd_line = './scripts/avocado multiplex nonexist'
        expected_rc = 2
        self.run_and_check(cmd_line, expected_rc)

    def test_run_mplex_sleeptest(self):
        cmd_line = './scripts/avocado run sleeptest --multiplex tests/sleeptest/sleeptest.mplx'
        expected_rc = 0
        self.run_and_check(cmd_line, expected_rc)

    def test_run_mplex_doublesleep(self):
        cmd_line = './scripts/avocado run "sleeptest sleeptest" --multiplex tests/sleeptest/sleeptest.mplx'
        expected_rc = 0
        self.run_and_check(cmd_line, expected_rc)

    def test_run_mplex_failtest(self):
        cmd_line = './scripts/avocado run "sleeptest failtest" --multiplex tests/sleeptest/sleeptest.mplx'
        expected_rc = 1
        self.run_and_check(cmd_line, expected_rc)

    def test_run_mplex_timeout(self):
        with tempfile.NamedTemporaryFile(delete=False) as multiplex_file:
            multiplex_file.write(timeout_multiplex)
            multiplex_file.close()
            cmd_line = ('./scripts/avocado run "sleeptest" --multiplex %s' %
                        multiplex_file.name)
            expected_rc = 1
            try:
                self.run_and_check(cmd_line, expected_rc)
            finally:
                os.unlink(multiplex_file.name)

if __name__ == '__main__':
    unittest.main()
