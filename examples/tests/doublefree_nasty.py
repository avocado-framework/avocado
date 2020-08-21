import os
import shutil

from avocado import Test
from avocado.utils import build, process


class DoubleFreeTest(Test):

    """
    10% chance to execute double free exception.

    :avocado: tags=failure_expected,requires_c_compiler

    :param source: name of the source file located in a data directory
    """

    __binary = None     # filename of the compiled program

    def setUp(self):
        """
        Build 'doublefree'.
        """
        source = self.params.get('source', default='doublefree.c')
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
        Execute 'doublefree'.
        """
        cmd = os.path.join(self.workdir, self.__binary)
        cmd_result = process.run(cmd)
        self.log.info(cmd_result)
