import glob
import os
import sys
import tempfile
import shutil
import unittest

from avocado.core import exit_codes
from avocado.utils import process
from avocado.utils import script

from .. import AVOCADO, BASEDIR


class DiffTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        test = script.make_script(os.path.join(self.tmpdir, 'test'), 'exit 0')
        cmd_line = ('%s run %s '
                    '--external-runner /bin/bash '
                    '--job-results-dir %s --sysinfo=off --json -' %
                    (AVOCADO, test, self.tmpdir))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)
        self.jobdir = ''.join(glob.glob(os.path.join(self.tmpdir, 'job-*')))

        self.tmpdir2 = tempfile.mkdtemp(prefix='avocado_' + __name__)
        cmd_line = ('%s run %s '
                    '--external-runner /bin/bash '
                    '--job-results-dir %s --sysinfo=off --json -' %
                    (AVOCADO, test, self.tmpdir2))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)
        self.jobdir2 = ''.join(glob.glob(os.path.join(self.tmpdir2, 'job-*')))

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
        if AVOCADO.startswith(sys.executable):
            avocado_in_log = AVOCADO[len(sys.executable)+1:]
        else:
            avocado_in_log = AVOCADO
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
        shutil.rmtree(self.tmpdir)
        shutil.rmtree(self.tmpdir2)


if __name__ == '__main__':
    unittest.main()
