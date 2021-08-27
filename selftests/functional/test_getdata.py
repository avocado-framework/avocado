import os
import unittest

from avocado.core import exit_codes
from avocado.utils import process
from selftests.utils import AVOCADO, BASEDIR, TestCaseTmpDir


class GetData(TestCaseTmpDir):

    def test(self):
        test_path = os.path.join(BASEDIR, "selftests", ".data", "get_data.py")
        cmd_line = "%s run --disable-sysinfo --job-results-dir '%s' -- %s"
        cmd_line %= (AVOCADO, self.tmpdir.name, test_path)
        result = process.run(cmd_line)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)

    def test_varianter(self):
        test_path = os.path.join(BASEDIR, "selftests", ".data", "get_data.py")
        test_variants_path = os.path.join(BASEDIR, "selftests", ".data",
                                          "get_data.py.data", "get_data.json")
        cmd_line = ("%s run --disable-sysinfo --job-results-dir '%s' "
                    "--test-runner=runner "
                    "--json-variants-load %s -- %s")
        cmd_line %= (AVOCADO, self.tmpdir.name, test_variants_path, test_path)
        result = process.run(cmd_line)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)


if __name__ == '__main__':
    unittest.main()
