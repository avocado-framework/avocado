#!/usr/bin/python

import os
import shutil

from avocado import test
from avocado import job
from avocado.utils import build
from avocado.utils import process


class DataDirTest(test.Test):

    """
    Test that uses resources from the data dir.
    """

    def setUp(self):
        """
        Build 'datadir'.
        """
        c_file = self.get_data_path(self.params.get('source', 'datadir.c'))
        c_file_name = os.path.basename(c_file)
        dest_c_file = os.path.join(self.srcdir, c_file_name)
        shutil.copy(c_file, dest_c_file)
        build.make(self.srcdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args='datadir')

    def runTest(self):
        """
        Execute 'datadir'.
        """
        cmd = os.path.join(self.srcdir, 'datadir')
        cmd_result = process.run(cmd)
        self.log.info(cmd_result)


if __name__ == "__main__":
    job.main()
