import os
import tempfile
import unittest.mock

from avocado.core import settings

from .. import temp_dir_prefix


class DataDirTest(unittest.TestCase):

    def _get_temporary_dirs_mapping_and_config(self):
        """
        Creates a temporary bogus base data dir

        And returns a dictionary containing the temporary data dir paths and
        a the path to a configuration file contain those same settings
        """
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        base_dir = tempfile.TemporaryDirectory(prefix=prefix)
        test_dir = os.path.join(base_dir.name, 'tests')
        os.mkdir(test_dir)
        mapping = {'base_dir': base_dir.name,
                   'test_dir': test_dir,
                   'data_dir': os.path.join(base_dir.name, 'data'),
                   'logs_dir': os.path.join(base_dir.name, 'logs')}
        temp_settings = ('[datadir.paths]\n'
                         'base_dir = %(base_dir)s\n'
                         'test_dir = %(test_dir)s\n'
                         'data_dir = %(data_dir)s\n'
                         'logs_dir = %(logs_dir)s\n') % mapping
        config_file = tempfile.NamedTemporaryFile('w', delete=False)
        config_file.write(temp_settings)
        config_file.close()
        return (base_dir, mapping, config_file.name)

    def setUp(self):
        (self.base_dir,
         self.mapping,
         self.config_file_path) = self._get_temporary_dirs_mapping_and_config()

    def test_datadir_from_config(self):
        """
        When avocado.conf is present, honor the values coming from it.
        """
        stg = settings.Settings(self.config_file_path)
        # Trick the module to think we're on a system wide install
        stg.intree = False
        with unittest.mock.patch('avocado.core.data_dir.settings.settings', stg):
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
        with unittest.mock.patch('avocado.core.data_dir.time.strftime',
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
        # Initial settings with initial data_dir locations
        stg = settings.Settings(self.config_file_path)
        with unittest.mock.patch('avocado.core.data_dir.settings.settings', stg):
            from avocado.core import data_dir
            for key in self.mapping.keys():
                data_dir_func = getattr(data_dir, 'get_%s' % key)
                self.assertEqual(data_dir_func(), self.mapping[key])

        (self.alt_base_dir,  # pylint: disable=W0201
         self.alt_mapping,  # pylint: disable=W0201
         self.alt_config_file_path) = self._get_temporary_dirs_mapping_and_config()  # pylint: disable=W0201

        # Alternate setttings with different data_dir location
        alt_stg = settings.Settings(self.alt_config_file_path)
        with unittest.mock.patch('avocado.core.data_dir.settings.settings', alt_stg):
            for key in self.alt_mapping.keys():
                data_dir_func = getattr(data_dir, 'get_%s' % key)
                self.assertEqual(data_dir_func(), self.alt_mapping[key])

    def test_get_job_results_dir(self):
        from avocado.core import data_dir
        from avocado.core import job_id

        # First let's mock a jobs results directory
        #

        logs_dir = self.mapping.get('logs_dir')
        self.assertNotEqual(None, logs_dir)
        unique_id = job_id.create_unique_job_id()
        # Expected job results dir
        expected_jrd = data_dir.create_job_logs_dir(logs_dir, unique_id)

        # Now let's test some cases
        #

        self.assertEqual(None,
                         data_dir.get_job_results_dir(expected_jrd, logs_dir),
                         ("If passing a directory reference, it expects the id"
                          "file"))

        # Create the id file.
        id_file_path = os.path.join(expected_jrd, 'id')
        with open(id_file_path, 'w') as id_file:
            id_file.write("%s\n" % unique_id)
            id_file.flush()
            os.fsync(id_file)

        self.assertEqual(expected_jrd,
                         data_dir.get_job_results_dir(expected_jrd, logs_dir),
                         "It should get from the path to the directory")

        results_dirname = os.path.basename(expected_jrd)
        self.assertEqual(None,
                         data_dir.get_job_results_dir(results_dirname,
                                                      logs_dir),
                         "It should not get from a valid path to the directory")

        pwd = os.getcwd()
        os.chdir(logs_dir)
        self.assertEqual(expected_jrd,
                         data_dir.get_job_results_dir(results_dirname,
                                                      logs_dir),
                         "It should get from relative path to the directory")
        os.chdir(pwd)

        self.assertEqual(expected_jrd,
                         data_dir.get_job_results_dir(id_file_path, logs_dir),
                         "It should get from the path to the id file")

        self.assertEqual(expected_jrd,
                         data_dir.get_job_results_dir(unique_id, logs_dir),
                         "It should get from the id")

        another_id = job_id.create_unique_job_id()
        self.assertNotEqual(unique_id, another_id)
        self.assertEqual(None,
                         data_dir.get_job_results_dir(another_id, logs_dir),
                         "It should not get from unexisting job")

        self.assertEqual(expected_jrd,
                         data_dir.get_job_results_dir(unique_id[:7], logs_dir),
                         "It should get from partial id equals to 7 digits")

        self.assertEqual(expected_jrd,
                         data_dir.get_job_results_dir(unique_id[:4], logs_dir),
                         "It should get from partial id less than 7 digits")

        almost_id = unique_id[:7] + ('a' * (len(unique_id) - 7))
        self.assertNotEqual(unique_id, almost_id)
        self.assertEqual(None,
                         data_dir.get_job_results_dir(almost_id, logs_dir),
                         ("It should not get if the id is equal on only"
                          "the first 7 characters"))

        os.symlink(expected_jrd, os.path.join(logs_dir, 'latest'))
        self.assertEqual(expected_jrd,
                         data_dir.get_job_results_dir('latest', logs_dir),
                         "It should get from the 'latest' id")

        stg = settings.Settings(self.config_file_path)
        with unittest.mock.patch('avocado.core.data_dir.settings.settings',
                                 stg):
            self.assertEqual(expected_jrd,
                             data_dir.get_job_results_dir(unique_id),
                             "It should use the default base logs directory")

    def tearDown(self):
        os.unlink(self.config_file_path)
        self.base_dir.cleanup()
        # clean up alternate configuration file if set by the test
        if hasattr(self, 'alt_config_file_path'):
            os.unlink(self.alt_config_file_path)
        if hasattr(self, 'alt_base_dir'):
            self.alt_base_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
