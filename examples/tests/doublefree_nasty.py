#!/usr/bin/env python

import os
import shutil

from avocado import main
from avocado import Test
from avocado.utils import build
from avocado.utils import process


class DoubleFreeTest(Test):

    """
    10% chance to execute double free exception.

    :param source: name of the source file located in deps path
    """

    __binary = None     # filename of the compiled program

    def setUp(self):
        """
        Build 'doublefree'.
        """
        source = self.params.get('source', default='doublefree.c')
        c_file = os.path.join(self.datadir, source)
        shutil.copy(c_file, self.srcdir)
        self.__binary = source.rsplit('.', 1)[0]
        build.make(self.srcdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args=self.__binary)

    def test(self):
        """
        Execute 'doublefree'.
        """
        cmd = os.path.join(self.srcdir, self.__binary)
        cmd_result = process.run(cmd)
        self.log.info(cmd_result)

if __name__ == "__main__":
    main()
