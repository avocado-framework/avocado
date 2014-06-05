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


class OutputTest(unittest.TestCase):

    def test_output_doublefree(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run doublefree'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 1
        output = result.stdout + result.stderr
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        bad_string = 'double free or corruption'
        self.assertNotIn(bad_string, output,
                         "Libc double free can be seen in avocado "
                         "doublefree output:\n%s" % output)


if __name__ == '__main__':
    unittest.main()
