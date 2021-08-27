import glob
import os
import tempfile
import unittest

from avocado.core import exit_codes
from avocado.utils import process
from selftests.utils import AVOCADO, BASEDIR, TestCaseTmpDir


class DiffTests(TestCaseTmpDir):

    def setUp(self):
        super(DiffTests, self).setUp()
        cmd_line = ('%s run examples/tests/passtest.py '
                    '--job-results-dir %s --disable-sysinfo --json -' %
                    (AVOCADO, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)
        self.jobdir = ''.join(glob.glob(os.path.join(self.tmpdir.name, 'job-*')))

        self.tmpdir2 = tempfile.TemporaryDirectory(prefix=self.tmpdir.name)
        cmd_line = ('%s run examples/tests/warntest.py '
                    '--job-results-dir %s --disable-sysinfo --json -' %
                    (AVOCADO, self.tmpdir2.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)
        self.jobdir2 = ''.join(glob.glob(os.path.join(self.tmpdir2.name, 'job-*')))

    def run_and_check(self, cmd_line, expected_rc):
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        return result

    @unittest.skipIf(os.environ.get("RUNNING_COVERAGE"), "Running coverage")
    def test_diff(self):
        cmd_line = ('%s diff %s %s' %
                    (AVOCADO, self.jobdir, self.jobdir2))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        result = self.run_and_check(cmd_line, expected_rc)
        # Avocado will see the main module on the command line
        avocado_in_log = os.path.join(BASEDIR, 'avocado', '__main__.py')
        self.assertIn(b"# COMMAND LINE", result.stdout)
        self.assertIn("-%s run" % avocado_in_log, result.stdout_text)
        self.assertIn("+%s run" % avocado_in_log, result.stdout_text)

    def test_diff_nocmdline(self):
        cmd_line = ('%s diff %s %s --diff-filter nocmdline' %
                    (AVOCADO, self.jobdir, self.jobdir2))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        result = self.run_and_check(cmd_line, expected_rc)
        self.assertNotIn(b"# COMMAND LINE", result.stdout)

    def tearDown(self):
        self.tmpdir.cleanup()
        self.tmpdir2.cleanup()


if __name__ == '__main__':
    unittest.main()
