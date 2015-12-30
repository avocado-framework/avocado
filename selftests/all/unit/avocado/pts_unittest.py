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
# Author: Cleber Rosa <crosa@redhat.com>


import os
import sys
import unittest

from avocado.utils import pts

# simple magic for using scripts within a source tree
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
basedir = os.path.dirname(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)


class PtsTest(unittest.TestCase):

    def test_create_destroy(self):
        master, slave, path = pts.openpty()
        self.assertTrue(os.path.exists(path))
        os.close(slave)
        os.close(master)
        self.assertFalse(os.path.exists(path))

if __name__ == '__main__':
    unittest.main()
