import os
import shutil

from avocado import Test
from avocado.utils import build, gdb


class PrintVariableTest(Test):

    """
    This demonstrates the GDB API
    1) it executes C program which prints MY VARIABLE 'A' IS: 0
    2) using GDB it modifies the variable to ff
    3) checks the output

    :avocado: tags=requires_c_compiler

    :param source: name of the source file located in a data directory
    """

    __binary = None    # filename of the compiled program

    def setUp(self):
        """
        Build 'print_variable'.
        """
        source = self.params.get('source', default='print_variable.c')
        c_file = self.get_data(source)
        if c_file is None:
            self.cancel('Test is missing data file %s' % source)
        shutil.copy(c_file, self.workdir)
        self.__binary = source.rsplit('.', 1)[0]
        build.make(self.workdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args=self.__binary)

    def test(self):
        """
        Execute 'print_variable'.
        """
        path = os.path.join(self.workdir, self.__binary)
        app = gdb.GDB()
        app.set_file(path)
        app.set_break(6)
        app.run()
        self.log.info("\n".join([line.decode() for line in app.read_until_break()]))
        app.cmd("set variable a = 0xff")
        app.cmd("c")
        out = "\n".join([line.decode() for line in app.read_until_break()])
        self.log.info(out)
        app.exit()
        self.assertIn("MY VARIABLE 'A' IS: ff", out)
