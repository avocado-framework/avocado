import os
import shutil

from avocado import Test
from avocado.utils import build, process


class CAbort(Test):

    """
    A test that calls C standard lib function abort().

    :avocado: tags=requires_c_compiler
    """

    def setUp(self):
        """
        Build 'abort'.
        """
        source = self.params.get('source', default='abort.c')
        c_file = self.get_data(source)
        if c_file is None:
            self.cancel('Test is missing data file %s' % source)
        c_file_name = os.path.basename(c_file)
        dest_c_file = os.path.join(self.workdir, c_file_name)
        shutil.copy(c_file, dest_c_file)
        build.make(self.workdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args='abort')

    def test(self):
        """
        Execute 'abort'.
        """
        cmd = os.path.join(self.workdir, 'abort')
        cmd_result = process.run(cmd, ignore_status=True)
        self.log.info(cmd_result)
        expected_result = -6  # SIGABRT = 6
        self.assertEqual(cmd_result.exit_status, expected_result)
