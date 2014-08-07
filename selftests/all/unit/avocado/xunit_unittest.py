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

import argparse
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
from avocado import job


class ParseXMLError(Exception):
    pass


class xUnitSucceedTest(unittest.TestCase):

    def setUp(self):
        self.tmpfile = mkstemp()
        args = argparse.Namespace()
        args.xunit_output = self.tmpfile[1]
        self.test_result = xunit.xUnitTestResult(args=args)
        self.test_result.start_tests()
        self.test1 = test.Test(job=job.Job())
        self.test1.status = 'PASS'
        self.test1.time_elapsed = 1.23

    def tearDown(self):
        os.close(self.tmpfile[0])
        os.remove(self.tmpfile[1])

    def testAddSuccess(self):
        self.test_result.start_test(self.test1)
        self.test_result.end_test(self.test1.get_state())
        self.test_result.end_tests()
        self.assertTrue(self.test_result.xml)
        with open(self.test_result.output) as fp:
            xml = fp.read()
        try:
            dom = minidom.parseString(xml)
        except Exception, details:
            raise ParseXMLError("Error parsing XML: '%s'.\nXML Contents:\n%s" % (details, xml))
        self.assertTrue(dom)
        els = dom.getElementsByTagName('testcase')
        self.assertEqual(len(els), 1)


if __name__ == '__main__':
    unittest.main()
