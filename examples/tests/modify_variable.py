#!/usr/bin/env python

import os
import shutil

from avocado import main
from avocado import Test
from avocado.utils import gdb
from avocado.utils import build


class PrintVariableTest(Test):

    """
    This demonstrates the GDB API
    1) it executes C program which prints MY VARIABLE 'A' IS: 0
    2) using GDB it modifies the variable to ff
    3) checks the output

    :param source: path to the source file relative to deps dir.
    """

    __binary = None    # filename of the compiled program

    def setUp(self):
        """
        Build 'print_variable'.
        """
        source = self.params.get('source', default='print_variable.c')
        c_file = os.path.join(self.datadir, source)
        shutil.copy(c_file, self.srcdir)
        self.__binary = source.rsplit('.', 1)[0]
        build.make(self.srcdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args=self.__binary)

    def test(self):
        """
        Execute 'print_variable'.
        """
        path = os.path.join(self.srcdir, self.__binary)
        app = gdb.GDB()
        app.set_file(path)
        app.set_break(6)
        app.run()
        self.log.info("\n".join(app.read_until_break()))
        app.cmd("set variable a = 0xff")
        app.cmd("c")
        out = "\n".join(app.read_until_break())
        self.log.info(out)
        app.exit()
        self.assertIn("MY VARIABLE 'A' IS: ff", out)


if __name__ == "__main__":
    main()
