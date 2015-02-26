#!/usr/bin/python

import os

from avocado import test
from avocado import job
from avocado import gdb
from avocado.utils import build
from avocado.utils import process


class PrintVariableTest(test.Test):

    """
    This demonstrates the GDB API
    1) it executes C program which prints MY VARIABLE 'A' IS: 0
    2) using GDB it modifies the variable to ff
    3) checks the output
    """

    default_params = {'source': 'print_variable.c'}

    def setup(self):
        """
        Build 'print_variable'.
        """
        self.cwd = os.getcwd()
        c_file = self.get_data_path(self.params.source)
        self.srcdir = os.path.dirname(c_file)
        build.make(self.srcdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args='print_variable')

    def action(self):
        """
        Execute 'print_variable'.
        """
        path = os.path.join(self.srcdir, 'print_variable')
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

    def cleanup(self):
        """
        Clean up 'print_variable'.
        """
        os.unlink(os.path.join(self.srcdir, 'print_variable'))

if __name__ == "__main__":
    job.main()
