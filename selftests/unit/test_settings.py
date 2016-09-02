import os
import sys
import tempfile

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import settings

example_1 = """[foo]
str_key = frobnicate
int_key = 1
float_key = 1.25
bool_key = True
list_key = ['I', 'love', 'settings']
empty_key =
path = ~/path/at/home
home_path = ~
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

    def testPathHomeDir(self):
        raw_from_settings = '~/path/at/home'
        path_from_settings = self.settings.get_value('foo', 'path', 'path')
        home_str_from_settings = self.settings.get_value('foo', 'home_path', str)
        self.assertEqual(path_from_settings[-13:],
                         raw_from_settings[-13:])
        self.assertGreaterEqual(len(path_from_settings),
                                len(raw_from_settings))
        self.assertEqual(os.path.expanduser(home_str_from_settings),
                         self.settings.get_value('foo', 'home_path', 'path'))

    def testPathOnStrKey(self):
        self.assertEqual(self.settings.get_value('foo', 'path', str),
                         '~/path/at/home')

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
