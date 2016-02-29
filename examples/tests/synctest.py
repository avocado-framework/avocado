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
        tarball_path = os.path.join(self.datadir, sync_tarball)
        archive.extract(tarball_path, self.srcdir)
        self.srcdir = os.path.join(self.srcdir, 'synctest')
        if self.params.get('debug_symbols', default=True):
            build.make(self.srcdir,
                       env={'CFLAGS': '-g -O0'},
                       extra_args='synctest')
        else:
            build.make(self.srcdir)

    def test(self):
        """
        Execute synctest with the appropriate params.
        """
        os.chdir(self.srcdir)
        path = os.path.join(os.getcwd(), 'synctest')
        cmd = ('%s %s %s' %
               (path, self.params.get('sync_length', default=100),
                self.params.get('sync_loop', default=10)))
        process.system(cmd)
        os.chdir(self.cwd)


if __name__ == "__main__":
    main()
