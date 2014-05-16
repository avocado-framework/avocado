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
# Author: Ruda Moura <rmoura@redhat.com>

import unittest
import os
import sys
from xml.dom import minidom
from tempfile import mkstemp

# simple magic for using scripts within a source tree
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
basedir = os.path.dirname(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.plugins import xunit
from avocado import test


class xUnitSucceedTest(unittest.TestCase):

    def setUp(self):
        self.tmpfile = mkstemp()
        self.test_result = xunit.xUnitTestResult()
        self.test_result.filename = self.tmpfile[1]
        self.test_result.start_tests()
        self.test1 = test.Test()
        self.test1.status = 'PASS'
        self.test1.time_elapsed = 1.23

    def tearDown(self):
        os.close(self.tmpfile[0])
        os.remove(self.tmpfile[1])

    def testAddSuccess(self):
        self.test_result.start_test(self.test1)
        self.test_result.end_test(self.test1)
        self.test_result.end_tests()
        self.assertTrue(self.test_result.xml)
        with open(self.test_result.filename) as fp:
            xml = fp.read()
        dom = minidom.parseString(xml)
        self.assertTrue(dom)
        els = dom.getElementsByTagName('testcase')
        self.assertEqual(len(els), 1)


if __name__ == '__main__':
    unittest.main()
