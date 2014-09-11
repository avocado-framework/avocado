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

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import process


class StandaloneTests(unittest.TestCase):

    def setUp(self):
        self.original_pypath = os.environ.get('PYTHONPATH')
        if self.original_pypath is not None:
            os.environ['PYTHONPATH'] = '%s:%s' % (basedir, self.original_pypath)
        else:
            os.environ['PYTHONPATH'] = '%s' % basedir

    def run_and_check(self, cmd_line, expected_rc, tstname):
        os.chdir(basedir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Stand alone %s did not return rc "
                         "%d:\n%s" % (tstname, expected_rc, result))

    def test_sleeptest(self):
        cmd_line = './examples/tests/sleeptest.py'
        expected_rc = 0
        self.run_and_check(cmd_line, expected_rc, 'sleeptest')

    def test_skiptest(self):
        cmd_line = './examples/tests/skiptest.py'
        expected_rc = 0
        self.run_and_check(cmd_line, expected_rc, 'skiptest')

    def test_failtest(self):
        cmd_line = './examples/tests/failtest.py'
        expected_rc = 1
        self.run_and_check(cmd_line, expected_rc, 'failtest')

    def test_errortest(self):
        cmd_line = './examples/tests/errortest.py'
        expected_rc = 1
        self.run_and_check(cmd_line, expected_rc, 'errortest')

    def test_warntest(self):
        cmd_line = './examples/tests/warntest.py'
        expected_rc = 1
        self.run_and_check(cmd_line, expected_rc, 'warntest')

if __name__ == '__main__':
    unittest.main()
