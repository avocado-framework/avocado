#!/usr/bin/python

import os

from avocado import test
from avocado import job
from avocado.utils import archive
from avocado.utils import build
from avocado.utils import process


class SyncTest(test.Test):

    """
    Execute the synctest test suite.
    """

    def setUp(self):
        """
        Build the synctest suite.
        """
        self.cwd = os.getcwd()
        tarball_path = self.get_data_path(self.params.get('sync_tarball',
                                                          'synctest.tar.bz2'))
        archive.extract(tarball_path, self.srcdir)
        self.srcdir = os.path.join(self.srcdir, 'synctest')
        if self.params.get('debug_symbols', True):
            build.make(self.srcdir,
                       env={'CFLAGS': '-g -O0'},
                       extra_args='synctest')
        else:
            build.make(self.srcdir)

    def runTest(self):
        """
        Execute synctest with the appropriate params.
        """
        os.chdir(self.srcdir)
        path = os.path.join(os.getcwd(), 'synctest')
        cmd = ('%s %s %s' %
               (path, self.params.get('sync_length', 100),
                self.params.get('sync_loop', 10)))
        process.system(cmd)
        os.chdir(self.cwd)


if __name__ == "__main__":
    job.main()
