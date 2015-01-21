#!/usr/bin/python

import os

from avocado import test
from avocado import job
from avocado.utils import build
from avocado.utils import process


class DoubleFreeTest(test.Test):

    """
    Double free test case.
    """

    default_params = {'source': 'doublefree.c'}

    def setup(self):
        """
        Build 'doublefree'.
        """
        self.cwd = os.getcwd()
        c_file = self.get_data_path(self.params.source)
        self.srcdir = os.path.dirname(c_file)
        build.make(self.srcdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args='doublefree')

    def action(self):
        """
        Execute 'doublefree'.
        """
        cmd = os.path.join(self.srcdir, 'doublefree')
        cmd_result = process.run(cmd)
        self.log.info(cmd_result)

    def cleanup(self):
        """
        Clean up 'doublefree'.
        """
        os.unlink(os.path.join(self.srcdir, 'doublefree'))

if __name__ == "__main__":
    job.main()
