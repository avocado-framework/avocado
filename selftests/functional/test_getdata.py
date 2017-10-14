import os
import shutil
import tempfile
import unittest

from avocado.core import exit_codes
from avocado.utils import process


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)

AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD", "./scripts/avocado")


class GetData(unittest.TestCase):

    def setUp(self):
        os.chdir(basedir)
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def test(self):
        test_path = os.path.join(basedir, "selftests", ".data", "get_data.py")
        test_variants_path = os.path.join(basedir, "selftests", ".data",
                                          "get_data.py.data", "get_data.yaml")
        cmd_line = "%s run --sysinfo=off --job-results-dir '%s' -m %s -- %s"
        cmd_line %= (AVOCADO, self.tmpdir, test_variants_path, test_path)
        result = process.run(cmd_line)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
