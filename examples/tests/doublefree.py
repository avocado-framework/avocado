#!/usr/bin/env python

import os
import shutil

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
        c_file = self.get_data(source)
        if c_file is None:
            self.cancel('Test is missing data file %s' % source)
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
        cmd_result = process.run(cmd, ignore_status=True,
                                 env={'MALLOC_CHECK_': '1'})
        self.log.info(cmd_result)
        pattern = 'free(): invalid pointer'
        self.assertTrue(pattern in cmd_result.stderr,
                        msg='Could not find pattern %s in stderr' % pattern)


if __name__ == "__main__":
    main()
