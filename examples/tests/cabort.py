#!/usr/bin/python

import os
import shutil

from avocado import test
from avocado.core import job
from avocado.utils import build
from avocado.utils import process


class CAbort(test.Test):

    """
    A test that calls C standard lib function abort().
    """

    def setUp(self):
        """
        Build 'abort'.
        """
        c_file = self.get_data_path(self.params.get('source', 'abort.c'))
        c_file_name = os.path.basename(c_file)
        dest_c_file = os.path.join(self.srcdir, c_file_name)
        shutil.copy(c_file, dest_c_file)
        build.make(self.srcdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args='abort')

    def runTest(self):
        """
        Execute 'abort'.
        """
        cmd = os.path.join(self.srcdir, 'abort')
        cmd_result = process.run(cmd, ignore_status=True)
        self.log.info(cmd_result)
        expected_result = -6  # SIGABRT = 6
        self.assertEqual(cmd_result.exit_status, expected_result)


if __name__ == "__main__":
    job.main()
