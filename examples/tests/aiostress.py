#!/usr/bin/env python

import os
import shutil

from avocado import Test
from avocado import main
from avocado.utils import process


class Aiostress(Test):

    """
    aio-stress is a basic utility for testing the Linux kernel AIO api
    """

    def setUp(self):
        """
        Build 'aiostress'.
        Source:
         https://oss.oracle.com/~mason/aio-stress/aio-stress.c
        """
        aiostress_c = self.params.get('aiostress_c', default='aio-stress.c')
        c_path = self.get_data_path(aiostress_c)
        shutil.copy(c_path, self.srcdir)
        os.chdir(self.srcdir)
        # This requires libaio.h in order to build
        process.run('gcc -Wall -laio -lpthread -o aio-stress %s' % aiostress_c)

    def test(self):
        """
        Run aiostress
        """
        os.chdir(self.srcdir)
        cmd = ('./aio-stress foo')
        process.run(cmd)


if __name__ == "__main__":
    main()
