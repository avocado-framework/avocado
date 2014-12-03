#!/usr/bin/env python

import unittest
import os
import sys
import shutil
import tempfile

from flexmock import flexmock

# simple magic for using scripts within a source tree
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
basedir = os.path.dirname(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado import settings


def _get_bogus_settings(args):
    return ('[runner]\n'
            'base_dir = %(base_dir)s\n'
            'test_dir = %(test_dir)s\n'
            'data_dir = %(data_dir)s\n'
            'logs_dir = %(logs_dir)s\n'
            'tmp_dir = %(tmp_dir)s\n') % args


class DataDirTest(unittest.TestCase):

    def setUp(self):
        tbase = tempfile.mkdtemp(prefix='avocado_datadir_unittest')
        tdir = os.path.join(tbase, 'tests')
        tdata = os.path.join(tbase, 'data')
        tlogs = os.path.join(tbase, 'logs')
        ttmp = os.path.join(tbase, 'tmp')
        self.mapping = {'base_dir': tbase, 'test_dir': tdir, 'data_dir': tdata,
                        'logs_dir': tlogs, 'tmp_dir': ttmp}
        self.config_file = tempfile.NamedTemporaryFile(delete=False)
        self.config_file.write(_get_bogus_settings(self.mapping))
        self.config_file.close()

    def testDataDirFromConfig(self):
        """
        When avocado.conf is present, honor the values coming from it.
        """
        stg = settings.Settings(self.config_file.name)
        # Trick the module to think we're on a system wide install
        stg.intree = False
        flexmock(settings, settings=stg)
        from avocado.core import data_dir
        flexmock(data_dir, settings=stg)
        self.assertFalse(data_dir.settings.intree)
        reload(data_dir)
        for key in self.mapping.keys():
            data_dir_func = getattr(data_dir, 'get_%s' % key)
            self.assertEqual(data_dir_func(), stg.get_value('runner', key))
        del data_dir

    def tearDown(self):
        os.unlink(self.config_file.name)
        shutil.rmtree(self.mapping['base_dir'])

if __name__ == '__main__':
    unittest.main()
