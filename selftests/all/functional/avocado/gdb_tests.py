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
# Copyright: Red Hat Inc. 2014
# Author: Cleber Rosa <cleber@redhat.com>

import os
import sys
import unittest

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado import runtime
from avocado.utils import process


class GDBPluginTest(unittest.TestCase):

    def test_gdb_prerun_commands(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --gdb-prerun-commands=/dev/null sleeptest'
        process.run(cmd_line)

    def test_gdb_multiple_prerun_commands(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --gdb-prerun-commands=/dev/null '
                    '--gdb-prerun-commands=foo:/dev/null sleeptest')
        process.run(cmd_line)

if __name__ == '__main__':
    unittest.main()
