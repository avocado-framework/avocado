import os
import sys
import unittest
import shutil
import tempfile

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.insert(0, basedir)

from avocado.utils import process


class GDBPluginTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_gdb_prerun_commands(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--gdb-prerun-commands=/dev/null passtest' % self.tmpdir)
        process.run(cmd_line)

    def test_gdb_multiple_prerun_commands(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off --gdb-prerun-commands=/dev/null '
                    '--gdb-prerun-commands=foo:/dev/null passtest' % self.tmpdir)
        process.run(cmd_line)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

if __name__ == '__main__':
    unittest.main()
