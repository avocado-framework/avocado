import os
import tempfile
import unittest

from avocado.core import exit_codes
from avocado.utils import process

from .. import AVOCADO, BASEDIR, temp_dir_prefix


class GetData(unittest.TestCase):

    def setUp(self):
        os.chdir(BASEDIR)
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    def test(self):
        test_path = os.path.join(BASEDIR, "selftests", ".data", "get_data.py")
        test_variants_path = os.path.join(BASEDIR, "selftests", ".data",
                                          "get_data.py.data", "get_data.yaml")
        cmd_line = "%s run --sysinfo=off --job-results-dir '%s' -m %s -- %s"
        cmd_line %= (AVOCADO, self.tmpdir.name, test_variants_path, test_path)
        result = process.run(cmd_line)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)

    def tearDown(self):
        self.tmpdir.cleanup()


if __name__ == '__main__':
    unittest.main()
