import unittest
import os
import shutil
import tempfile

from flexmock import flexmock

from avocado.core import settings


def _get_bogus_settings(args):
    return ('[datadir.paths]\n'
            'base_dir = %(base_dir)s\n'
            'test_dir = %(test_dir)s\n'
            'data_dir = %(data_dir)s\n'
            'logs_dir = %(logs_dir)s\n') % args


class DataDirTest(unittest.TestCase):

    def setUp(self):
        tbase = tempfile.mkdtemp(prefix='avocado_' + __name__)
        tdir = os.path.join(tbase, 'tests')
        tdata = os.path.join(tbase, 'data')
        tlogs = os.path.join(tbase, 'logs')
        self.mapping = {'base_dir': tbase, 'test_dir': tdir, 'data_dir': tdata,
                        'logs_dir': tlogs}
        self.config_file = tempfile.NamedTemporaryFile(delete=False)
        self.config_file.write(_get_bogus_settings(self.mapping))
        self.config_file.close()

    def testDataDirFromConfig(self):
        """
        When avocado.conf is present, honor the values coming from it.
        """
        stg_orig = settings.settings
        stg = settings.Settings(self.config_file.name)
        try:
            # Trick the module to think we're on a system wide install
            stg.intree = False
            flexmock(settings, settings=stg)
            from avocado.core import data_dir
            flexmock(data_dir, settings=stg)
            self.assertFalse(data_dir.settings.intree)
            reload(data_dir)
            for key in self.mapping.keys():
                data_dir_func = getattr(data_dir, 'get_%s' % key)
                self.assertEqual(data_dir_func(), stg.get_value('datadir.paths', key))
        finally:
            flexmock(settings, settings=stg_orig)
            reload(data_dir)
        del data_dir

    def testUniqueLogDir(self):
        """
        Tests that multiple queries for a logdir at the same time provides
        unique results.
        """
        from avocado.core import data_dir
        flexmock(data_dir.time).should_receive('strftime').and_return("date")
        logdir = os.path.join(self.mapping['base_dir'], "foor", "bar", "baz")
        path_prefix = os.path.join(logdir, "job-date-")
        uid = "1234567890"*4
        for i in xrange(7, 40):
            path = data_dir.create_job_logs_dir(logdir, uid)
            self.assertEqual(path, path_prefix + uid[:i])
            self.assertTrue(os.path.exists(path))
        path = data_dir.create_job_logs_dir(logdir, uid)
        self.assertEqual(path, path_prefix + uid + ".0")
        self.assertTrue(os.path.exists(path))
        path = data_dir.create_job_logs_dir(logdir, uid)
        self.assertEqual(path, path_prefix + uid + ".1")
        self.assertTrue(os.path.exists(path))

    def tearDown(self):
        os.unlink(self.config_file.name)
        shutil.rmtree(self.mapping['base_dir'])

if __name__ == '__main__':
    unittest.main()
