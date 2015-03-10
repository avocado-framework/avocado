#!/usr/bin/python

import os

import avocado

from avocado.utils import archive
from avocado.utils import build
from avocado.utils import process


class SyncTest(avocado.Test):

    """
    Execute the synctest test suite.
    """
    default_params = {'sync_tarball': 'synctest.tar.bz2',
                      'sync_length': 100,
                      'sync_loop': 10,
                      'debug_symbols': True}

    def setup(self):
        """
        Build the synctest suite.
        """
        self.cwd = os.getcwd()
        tarball_path = self.get_data_path(self.params.sync_tarball)
        archive.extract(tarball_path, self.srcdir)
        self.srcdir = os.path.join(self.srcdir, 'synctest')
        if self.params.debug_symbols:
            build.make(self.srcdir,
                       env={'CFLAGS': '-g -O0'},
                       extra_args='synctest')
        else:
            build.make(self.srcdir)

    def action(self):
        """
        Execute synctest with the appropriate params.
        """
        os.chdir(self.srcdir)
        path = os.path.join(os.getcwd(), 'synctest')
        cmd = ('%s %s %s' %
               (path, self.params.sync_length, self.params.sync_loop))
        process.system(cmd)
        os.chdir(self.cwd)


if __name__ == "__main__":
    avocado.main()
