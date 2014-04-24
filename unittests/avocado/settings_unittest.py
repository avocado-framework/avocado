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
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
basedir = os.path.dirname(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado import settings

example_1 = """[foo]
str_key = frobnicate
int_key = 1
float_key = 1.25
bool_key = True
list_key = I, love, settings
empty_key =
"""


class SettingsTest(unittest.TestCase):

    def setUp(self):
        self.config_file = tempfile.NamedTemporaryFile(delete=False)
        self.config_file.write(example_1)
        self.config_file.close()
        self.settings = settings.Settings(self.config_file.name)

    def testStringConversion(self):
        self.assertEqual(self.settings.get_value('foo', 'str_key', str),
                         'frobnicate')

    def testIntConversion(self):
        self.assertEqual(self.settings.get_value('foo', 'int_key', int), 1)

    def testFloatConversion(self):
        self.assertEqual(self.settings.get_value('foo', 'float_key', float),
                         1.25)

    def testBoolConversion(self):
        self.assertTrue(self.settings.get_value('foo', 'bool_key', bool))

    def testListConversion(self):
        self.assertEqual(self.settings.get_value('foo', 'list_key', list),
                         ['I', 'love', 'settings'])

    def testDefault(self):
        self.assertEqual(self.settings.get_value('foo', 'non_existing',
                                                 str, "ohnoes"), "ohnoes")

    def testNonExistingKey(self):
        with self.assertRaises(settings.SettingsError):
            self.settings.get_value('foo', 'non_existing', str)

    def testAllowBlankTrueStr(self):
        self.assertEqual(self.settings.get_value('foo', 'empty_key', str,
                                                 allow_blank=True), "")

    def testAllowBlankTrueInt(self):
        self.assertEqual(self.settings.get_value('foo', 'empty_key', int,
                                                 allow_blank=True), 0)

    def testAllowBlankTrueFloat(self):
        self.assertEqual(self.settings.get_value('foo', 'empty_key', float,
                                                 allow_blank=True), 0.0)

    def testAllowBlankTrueList(self):
        self.assertEqual(self.settings.get_value('foo', 'empty_key', list,
                                                 allow_blank=True), [])

    def testAllowBlankTrueBool(self):
        self.assertEqual(self.settings.get_value('foo', 'empty_key', bool,
                                                 allow_blank=True), False)

    def testAllowBlankTrueOther(self):
        self.assertEqual(self.settings.get_value('foo', 'empty_key', 'baz',
                                                 allow_blank=True), None)

    def testAllowBlankFalse(self):
        with self.assertRaises(settings.SettingsError):
            self.settings.get_value('foo', 'empty_key', str)

    def tearDown(self):
        os.unlink(self.config_file.name)

if __name__ == '__main__':
    unittest.main()
