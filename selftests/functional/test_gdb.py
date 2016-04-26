import os
import sys
import shutil
import tempfile

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.utils import process

basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


class GDBPluginTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def test_gdb_prerun_commands(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--gdb-prerun-commands=/dev/null passtest.py' % self.tmpdir)
        process.run(cmd_line)

    def test_gdb_multiple_prerun_commands(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--gdb-prerun-commands=/dev/null '
                    '--gdb-prerun-commands=foo:/dev/null passtest.py'
                    % self.tmpdir)
        process.run(cmd_line)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

if __name__ == '__main__':
    unittest.main()
