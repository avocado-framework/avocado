import os
import tempfile
import unittest

from avocado.core.future import settings

example = """[foo]
bar = default from file
non_registered = this should be ignored
"""


class SettingsTest(unittest.TestCase):

    def setUp(self):
        self.config_file = tempfile.NamedTemporaryFile('w', delete=False)
        self.config_file.write(example)
        self.config_file.close()

    def test_non_registered_option(self):
        """Config file options that are not registered should be ignored.

        This should force plugins to run register_option().
        """
        stgs = settings.Settings(self.config_file.name)
        config = stgs.as_dict()
        self.assertIsNone(config.get('foo.non_registered'))

    def test_override_default(self):
        """Test if default option is being overwritten by configfile."""

        stgs = settings.Settings(self.config_file.name)
        default = 'default from code'
        stgs.register_option(section='foo',
                             key='bar',
                             default=default,
                             help_msg='just a test')
        stgs.merge_with_configs()
        config = stgs.as_dict()
        self.assertEqual(config.get('foo.bar'), 'default from file')

    def test_non_existing_key(self):
        stgs = settings.Settings(self.config_file.name)
        config = stgs.as_dict()
        self.assertIsNone(config.get('foo.non_existing'))

    def test_bool(self):
        stgs = settings.Settings(self.config_file.name)
        stgs.register_option(section='foo',
                             key='bar',
                             default=False,
                             key_type=bool,
                             help_msg='just a test')
        config = stgs.as_dict()
        result = config.get('foo.bar')
        self.assertIsInstance(result, bool)
        self.assertFalse(result)

    def test_string(self):
        stgs = settings.Settings(self.config_file.name)
        stgs.register_option(section='foo',
                             key='bar',
                             default='just a test',
                             help_msg='just a test')
        config = stgs.as_dict()
        result = config.get('foo.bar')
        self.assertIsInstance(result, str)
        self.assertEqual(result, 'just a test')

    def test_list(self):
        stgs = settings.Settings(self.config_file.name)
        stgs.register_option(section='foo',
                             key='bar',
                             key_type=list,
                             default=[],
                             help_msg='just a test')
        config = stgs.as_dict()
        result = config.get('foo.bar')
        self.assertIsInstance(result, list)
        self.assertEqual(0, len(result))

    def tearDown(self):
        os.unlink(self.config_file.name)


class ConfigOption(unittest.TestCase):

    def test_as_list(self):
        config_option = settings.ConfigOption('namespace', 'help_message')
        self.assertEqual(config_option._as_list(''), [])
        self.assertEqual(config_option._as_list('[]'), [])
        self.assertEqual(config_option._as_list('[,,,]'), [])

    def test_as_list_fails(self):
        with self.assertRaises(ValueError):
            config_option = settings.ConfigOption('namespace', 'help_message')
            config_option._as_list(None)


if __name__ == '__main__':
    unittest.main()
