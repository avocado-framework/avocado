#!/usr/bin/env python

import os
import shutil
import signal
import sys

from avocado import Test
from avocado import main
from avocado.utils import build
from avocado.utils import process


class DoubleFreeTest(Test):

    """
    Double free test case.

    :avocado: tags=requires_c_compiler

    :param source: name of the source file located in deps path
    """

    def setUp(self):
        """
        Build 'doublefree'.
        """
        source = self.params.get('source', default='doublefree.c')
        c_file = os.path.join(self.datadir, source)
        c_file_name = os.path.basename(c_file)
        dest_c_file = os.path.join(self.srcdir, c_file_name)
        shutil.copy(c_file, dest_c_file)
        build.make(self.srcdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args='doublefree')

    def test(self):
        """
        Execute 'doublefree'.
        """
        cmd = os.path.join(self.srcdir, 'doublefree')
        cmd_result = process.run(cmd, ignore_status=True)
        self.log.info(cmd_result)
        expected_exit_status = -signal.SIGABRT
        output = cmd_result.stdout + cmd_result.stderr
        self.assertEqual(cmd_result.exit_status, expected_exit_status)
        if sys.platform.startswith('darwin'):
            pattern = 'pointer being freed was not allocated'
        else:
            pattern = 'double free or corruption'
        self.assertTrue(pattern in output,
                        msg='Could not find pattern %s in output %s' %
                            (pattern, output))


if __name__ == "__main__":
    main()
