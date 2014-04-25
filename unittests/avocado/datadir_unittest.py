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
    bogus_settings = '[runner]\n'
    bogus_settings += 'base_dir = %s\n' % args['base_dir']
    bogus_settings += 'test_dir = %s\n' % args['test_dir']
    bogus_settings += 'data_dir = %s\n' % args['data_dir']
    bogus_settings += 'logs_dir = %s\n' % args['logs_dir']
    bogus_settings += 'tmp_dir = %s\n' % args['tmp_dir']
    return bogus_settings


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
        When settings.ini is present, honor the values coming from it.
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
