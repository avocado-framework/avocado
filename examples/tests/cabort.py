#!/usr/bin/python

import os

from avocado import test
from avocado import job
from avocado.utils import build
from avocado.utils import process


class CAbort(test.Test):

    """
    A test that calls C standard lib function abort().
    """

    default_params = {'source': 'abort.c'}

    def setup(self):
        """
        Build 'abort'.
        """
        self.cwd = os.getcwd()
        c_file = self.get_data_path(self.params.source)
        self.srcdir = os.path.dirname(c_file)
        build.make(self.srcdir, extra_args='abort')

    def action(self):
        """
        Execute 'abort'.
        """
        cmd = os.path.join(self.srcdir, 'abort')
        cmd_result = process.run(cmd)
        self.log.info(cmd_result)

    def cleanup(self):
        """
        Clean up 'abort'.
        """
        os.unlink(os.path.join(self.srcdir, 'abort'))


if __name__ == "__main__":
    job.main()
