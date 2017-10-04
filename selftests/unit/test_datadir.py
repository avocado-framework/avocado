import unittest
import os
import shutil
import tempfile

try:
    from unittest import mock
except ImportError:
    import mock

from six.moves import xrange as range

from avocado.core import settings


class DataDirTest(unittest.TestCase):

    @staticmethod
    def _get_temporary_dirs_mapping_and_config():
        """
        Creates a temporary bogus base data dir

        And returns a dictionary containing the temporary data dir paths and
        a the path to a configuration file contain those same settings
        """
        base_dir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        mapping = {'base_dir': base_dir,
                   'test_dir': os.path.join(base_dir, 'tests'),
                   'data_dir': os.path.join(base_dir, 'data'),
                   'logs_dir': os.path.join(base_dir, 'logs')}
        temp_settings = ('[datadir.paths]\n'
                         'base_dir = %(base_dir)s\n'
                         'test_dir = %(test_dir)s\n'
                         'data_dir = %(data_dir)s\n'
                         'logs_dir = %(logs_dir)s\n') % mapping
        config_file = tempfile.NamedTemporaryFile('w', delete=False)
        config_file.write(temp_settings)
        config_file.close()
        return (mapping, config_file.name)

    def setUp(self):
        (self.mapping,
         self.config_file_path) = self._get_temporary_dirs_mapping_and_config()

    def test_datadir_from_config(self):
        """
        When avocado.conf is present, honor the values coming from it.
        """
        stg = settings.Settings(self.config_file_path)
        # Trick the module to think we're on a system wide install
        stg.intree = False
        with mock.patch('avocado.core.data_dir.settings.settings', stg):
            from avocado.core import data_dir
            self.assertFalse(data_dir.settings.settings.intree)
            for key in self.mapping.keys():
                data_dir_func = getattr(data_dir, 'get_%s' % key)
                self.assertEqual(data_dir_func(), stg.get_value('datadir.paths', key))
        # make sure that without the patch, we have a different value here
        self.assertTrue(data_dir.settings.settings.intree)

    def test_unique_log_dir(self):
        """
        Tests that multiple queries for a logdir at the same time provides
        unique results.
        """
        from avocado.core import data_dir
        with mock.patch('avocado.core.data_dir.time.strftime',
                        return_value="date_would_go_here"):
            logdir = os.path.join(self.mapping['base_dir'], "foor", "bar", "baz")
            path_prefix = os.path.join(logdir, "job-date_would_go_here-")
            uid = "1234567890"*4
            for i in range(7, 40):
                path = data_dir.create_job_logs_dir(logdir, uid)
                self.assertEqual(path, path_prefix + uid[:i])
                self.assertTrue(os.path.exists(path))
            path = data_dir.create_job_logs_dir(logdir, uid)
            self.assertEqual(path, path_prefix + uid + ".0")
            self.assertTrue(os.path.exists(path))
            path = data_dir.create_job_logs_dir(logdir, uid)
            self.assertEqual(path, path_prefix + uid + ".1")
            self.assertTrue(os.path.exists(path))

    def test_settings_dir_alternate_dynamic(self):
        """
        Tests that changes to the data_dir settings are applied dynamically

        To guarantee that, first the data_dir module is loaded. Then a new,
        alternate set of data directories are created and set in the
        "canonical" settings location, that is, avocado.core.settings.settings.

        No data_dir module reload should be necessary to get the new locations
        from data_dir APIs.
        """
        (self.alt_mapping,
         self.alt_config_file_path) = self._get_temporary_dirs_mapping_and_config()
        stg = settings.Settings(self.alt_config_file_path)
        with mock.patch('avocado.core.data_dir.settings.settings', stg):
            from avocado.core import data_dir
            for key in self.alt_mapping.keys():
                data_dir_func = getattr(data_dir, 'get_%s' % key)
                self.assertEqual(data_dir_func(), self.alt_mapping[key])
            del data_dir

    def tearDown(self):
        os.unlink(self.config_file_path)
        shutil.rmtree(self.mapping['base_dir'])
        # clean up alternate configuration file if set by the test
        if hasattr(self, 'alt_config_file_path'):
            os.unlink(self.alt_config_file_path)
        if hasattr(self, 'alt_mapping'):
            shutil.rmtree(self.alt_mapping['base_dir'])


if __name__ == '__main__':
    unittest.main()
