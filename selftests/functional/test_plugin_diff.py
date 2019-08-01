import glob
import os
import tempfile
import shlex
import unittest

from avocado.core import exit_codes
from avocado.utils import process
from avocado.utils import script

from .. import AVOCADO, BASEDIR, temp_dir_prefix


class DiffTests(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)
        test = script.make_script(os.path.join(self.tmpdir.name, 'test'), 'exit 0')
        cmd_line = ('%s run %s '
                    '--external-runner /bin/bash '
                    '--job-results-dir %s --sysinfo=off --json -' %
                    (AVOCADO, test, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)
        self.jobdir = ''.join(glob.glob(os.path.join(self.tmpdir.name, 'job-*')))

        self.tmpdir2 = tempfile.TemporaryDirectory(prefix=prefix)
        cmd_line = ('%s run %s '
                    '--external-runner /bin/bash '
                    '--job-results-dir %s --sysinfo=off --json -' %
                    (AVOCADO, test, self.tmpdir2.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)
        self.jobdir2 = ''.join(glob.glob(os.path.join(self.tmpdir2.name, 'job-*')))

    def run_and_check(self, cmd_line, expected_rc):
        os.chdir(BASEDIR)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        return result

    def test_diff(self):
        cmd_line = ('%s diff %s %s' %
                    (AVOCADO, self.jobdir, self.jobdir2))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        result = self.run_and_check(cmd_line, expected_rc)
        # Avocado won't know about the Python interpreter used on the
        # command line
        avocado_in_log = shlex.split(AVOCADO)[-1]
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
