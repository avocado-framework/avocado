import os
import shutil
import sys

from avocado import Test
from avocado.utils import build, process


class DoubleFreeTest(Test):

    """
    Double free test case.

    :avocado: tags=requires_c_compiler

    :param source: name of the source file located in a data directory
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
        dest_c_file = os.path.join(self.workdir, c_file_name)
        shutil.copy(c_file, dest_c_file)
        build.make(self.workdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args='doublefree')

    def test(self):
        """
        Execute 'doublefree'.
        """
        cmd = os.path.join(self.workdir, 'doublefree')
        cmd_result = process.run(cmd, ignore_status=True,
                                 env={'MALLOC_CHECK_': '1'})
        self.log.info(cmd_result)
        output = cmd_result.stdout + cmd_result.stderr
        if sys.platform.startswith('darwin'):
            pattern = b'pointer being freed was not allocated'
        else:
            pattern = b'free(): invalid pointer'
        self.assertTrue(pattern in output,
                        msg='Could not find pattern %s in output %s' %
                            (pattern, output))
