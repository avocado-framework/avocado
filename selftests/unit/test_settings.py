import os
import tempfile
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
        self.config_file = tempfile.NamedTemporaryFile('w', delete=False)
        self.config_file.write(example_1)
        self.config_file.close()
        self.settings = settings.Settings(self.config_file.name)

    def test_string_conversion(self):
        self.assertEqual(self.settings.get_value('foo', 'str_key', str),
                         'frobnicate')

    def test_int_conversion(self):
        self.assertEqual(self.settings.get_value('foo', 'int_key', int), 1)

    def test_float_conversion(self):
        self.assertEqual(self.settings.get_value('foo', 'float_key', float),
                         1.25)

    def test_bool_conversion(self):
        self.assertTrue(self.settings.get_value('foo', 'bool_key', bool))

    def test_path_homedir(self):
        raw_from_settings = '~/path/at/home'
        path_from_settings = self.settings.get_value('foo', 'path', 'path')
        home_str_from_settings = self.settings.get_value('foo', 'home_path', str)
        self.assertEqual(path_from_settings[-13:],
                         raw_from_settings[-13:])
        self.assertGreaterEqual(len(path_from_settings),
                                len(raw_from_settings))
        self.assertEqual(os.path.expanduser(home_str_from_settings),
                         self.settings.get_value('foo', 'home_path', 'path'))

    def test_path_on_str_key(self):
        self.assertEqual(self.settings.get_value('foo', 'path', str),
                         '~/path/at/home')

    def test_list_conversion(self):
        self.assertEqual(self.settings.get_value('foo', 'list_key', list),
                         ['I', 'love', 'settings'])

    def test_default(self):
        self.assertEqual(self.settings.get_value('foo', 'non_existing',
                                                 str, "ohnoes"), "ohnoes")

    def test_non_existing_key(self):
        with self.assertRaises(settings.SettingsError):
            self.settings.get_value('foo', 'non_existing', str)

    def test_allow_blank_true_str(self):
        self.assertEqual(self.settings.get_value('foo', 'empty_key', str,
                                                 allow_blank=True), "")

    def test_allow_blank_true_int(self):
        self.assertEqual(self.settings.get_value('foo', 'empty_key', int,
                                                 allow_blank=True), 0)

    def test_allow_blank_true_float(self):
        self.assertEqual(self.settings.get_value('foo', 'empty_key', float,
                                                 allow_blank=True), 0.0)

    def test_allow_blank_true_list(self):
        self.assertEqual(self.settings.get_value('foo', 'empty_key', list,
                                                 allow_blank=True), [])

    def test_allow_blank_true_bool(self):
        self.assertEqual(self.settings.get_value('foo', 'empty_key', bool,
                                                 allow_blank=True), False)

    def test_allow_blank_true_other(self):
        self.assertEqual(self.settings.get_value('foo', 'empty_key', 'baz',
                                                 allow_blank=True), None)

    def test_allow_blank_false(self):
        with self.assertRaises(settings.SettingsError):
            self.settings.get_value('foo', 'empty_key', str)

    def tearDown(self):
        os.unlink(self.config_file.name)


if __name__ == '__main__':
    unittest.main()
