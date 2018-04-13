import os
import tempfile
import shutil
import unittest

from avocado.core import exit_codes
from avocado.utils import process


BASEDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
BASEDIR = os.path.abspath(BASEDIR)

AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD", "./scripts/avocado")


class YamlLoaderTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def run_and_check(self, cmd_line, expected_rc, stdout_strings=None):
        os.chdir(BASEDIR)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        if stdout_strings is not None:
            for exp in stdout_strings:
                self.assertIn(exp, result.stdout, "%s not in stdout:"
                              "\n%s" % (exp, result))
        return result

    def test_replay(self):
        # Run source job
        tests = [b"passtest.py:PassTest.test", b"passtest.sh"]
        cmd = ('%s run --sysinfo=off --job-results-dir %s -- '
               'optional_plugins/loader_yaml/tests/.data/two_tests.yaml'
               % (AVOCADO, self.tmpdir))
        res = self.run_and_check(cmd, exit_codes.AVOCADO_ALL_OK, tests)
        # Run replay job
        for line in res.stdout.splitlines():
            if line.startswith(b"JOB LOG"):
                srcjob = line[13:]
                break
        else:
            self.fail("Unable to find 'JOB LOG' in:\n%s" % res)
        cmd = ('%s run --sysinfo=off --job-results-dir %s '
               '--replay %s' % (AVOCADO, self.tmpdir, srcjob.decode('utf-8')))
        self.run_and_check(cmd, exit_codes.AVOCADO_ALL_OK, tests)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
