#!/usr/bin/python

import os

from avocado import test
from avocado import job
from avocado.utils import build
from avocado.utils import process


class datadir(test.Test):

    """
    Test that uses resources from the data dir.
    """

    default_params = {'source': 'datadir.c'}

    def setup(self):
        """
        Build 'datadir'.
        """
        self.cwd = os.getcwd()
        c_file = self.get_data_path(self.params.source)
        self.srcdir = os.path.dirname(c_file)
        build.make(self.srcdir, extra_args='datadir')

    def action(self):
        """
        Execute 'datadir'.
        """
        cmd = os.path.join(self.srcdir, 'datadir')
        cmd_result = process.run(cmd)
        self.log.info(cmd_result)

    def cleanup(self):
        """
        Clean up 'datadir'.
        """
        os.unlink(os.path.join(self.srcdir, 'datadir'))

if __name__ == "__main__":
    job.main()
