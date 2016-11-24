#!/usr/bin/env python

import os
import shutil

from avocado import Test
from avocado import main
from avocado.utils import build
from avocado.utils import process


class CAbort(Test):

    """
    A test that calls C standard lib function abort().

    :avocado: tags=requires_c_compiler

    params:
    :param tarball: Path to the c-source file relative to deps dir.
    """

    def setUp(self):
        """
        Build 'abort'.
        """
        source = self.params.get('source', default='abort.c')
        c_file = os.path.join(self.datadir, source)
        c_file_name = os.path.basename(c_file)
        dest_c_file = os.path.join(self.srcdir, c_file_name)
        shutil.copy(c_file, dest_c_file)
        build.make(self.srcdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args='abort')

    def test(self):
        """
        Execute 'abort'.
        """
        cmd = os.path.join(self.srcdir, 'abort')
        cmd_result = process.run(cmd, ignore_status=True)
        self.log.info(cmd_result)
        expected_result = -6  # SIGABRT = 6
        self.assertEqual(cmd_result.exit_status, expected_result)


if __name__ == "__main__":
    main()
