#!/usr/bin/python

import os
import shutil

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
        c_file = self.get_data_path(self.params.source)
        c_file_name = os.path.basename(c_file)
        dest_c_file = os.path.join(self.srcdir, c_file_name)
        shutil.copy(c_file, dest_c_file)
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

if __name__ == "__main__":
    job.main()
