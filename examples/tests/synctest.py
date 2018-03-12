#!/usr/bin/env python

import os

from avocado import Test
from avocado import main
from avocado.utils import archive
from avocado.utils import build
from avocado.utils import process


class SyncTest(Test):

    """
    Execute the synctest test suite.

    :param sync_tarball: path to the tarball relative to deps dir.
    :param default_symbols: whether to build with debug symbols (bool)
    :param sync_length: how many data should by used in sync test
    :param sync_loop: how many writes should be executed in sync test
    """

    def setUp(self):
        """
        Build the synctest suite.
        """
        self.cwd = os.getcwd()
        sync_tarball = self.params.get('sync_tarball', '*', 'synctest.tar.bz2')
        tarball_path = self.get_data(sync_tarball)
        if tarball_path is None:
            self.cancel('Test is missing data file %s' % tarball_path)
        archive.extract(tarball_path, self.workdir)
        srcdir = os.path.join(self.workdir, 'synctest')
        os.chdir(srcdir)
        if self.params.get('debug_symbols', default=True):
            build.make(srcdir,
                       env={'CFLAGS': '-g -O0'},
                       extra_args='synctest',
                       allow_output_check='none')
        else:
            build.make(srcdir,
                       allow_output_check='none')

    def test(self):
        """
        Execute synctest with the appropriate params.
        """
        path = os.path.join(os.getcwd(), 'synctest')
        cmd = ('%s %s %s' %
               (path, self.params.get('sync_length', default=100),
                self.params.get('sync_loop', default=10)))
        process.system(cmd)
        os.chdir(self.cwd)


if __name__ == "__main__":
    main()
