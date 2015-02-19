#!/usr/bin/python

import os
import shutil

from avocado import job
from avocado import test
from avocado.utils import build
from avocado.utils import process


class DoubleFreeTest(test.Test):

    """
    10% chance to execute double free exception.
    """

    default_params = {'source': 'doublefree.c'}
    __binary = None     # filename of the compiled program

    def setup(self):
        """
        Build 'doublefree'.
        """
        c_file = self.get_data_path(self.params.source)
        shutil.copy(c_file, self.srcdir)
        self.__binary = self.params['source'].rsplit('.', 1)[0]
        build.make(self.srcdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args=self.__binary)

    def action(self):
        """
        Execute 'doublefree'.
        """
        cmd = os.path.join(self.srcdir, self.__binary)
        cmd_result = process.run(cmd)
        self.log.info(cmd_result)

if __name__ == "__main__":
    job.main()
