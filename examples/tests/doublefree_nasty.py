#!/usr/bin/python

import os
import shutil

from avocado.core import job
from avocado import test
from avocado.utils import build
from avocado.utils import process


class DoubleFreeTest(test.Test):

    """
    10% chance to execute double free exception.
    """

    __binary = None     # filename of the compiled program

    def setUp(self):
        """
        Build 'doublefree'.
        """
        source = self.params.get('source', 'doublefree.c')
        c_file = self.get_data_path(source)
        shutil.copy(c_file, self.srcdir)
        self.__binary = source.rsplit('.', 1)[0]
        build.make(self.srcdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args=self.__binary)

    def runTest(self):
        """
        Execute 'doublefree'.
        """
        cmd = os.path.join(self.srcdir, self.__binary)
        cmd_result = process.run(cmd)
        self.log.info(cmd_result)

if __name__ == "__main__":
    job.main()
