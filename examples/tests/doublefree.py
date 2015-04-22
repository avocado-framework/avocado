#!/usr/bin/python

import os
import shutil
import signal

from avocado import test
from avocado.core import job
from avocado.utils import build
from avocado.utils import process


class DoubleFreeTest(test.Test):

    """
    Double free test case.
    """

    def setUp(self):
        """
        Build 'doublefree'.
        """
        c_file = self.get_data_path(self.params.get('source', 'doublefree.c'))
        c_file_name = os.path.basename(c_file)
        dest_c_file = os.path.join(self.srcdir, c_file_name)
        shutil.copy(c_file, dest_c_file)
        build.make(self.srcdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args='doublefree')

    def runTest(self):
        """
        Execute 'doublefree'.
        """
        cmd = os.path.join(self.srcdir, 'doublefree')
        cmd_result = process.run(cmd, ignore_status=True)
        self.log.info(cmd_result)
        expected_exit_status = -signal.SIGABRT
        output = cmd_result.stdout + cmd_result.stderr
        self.assertEqual(cmd_result.exit_status, expected_exit_status)
        self.assertIn('double free or corruption', output)


if __name__ == "__main__":
    job.main()
