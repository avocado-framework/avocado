import os
import tempfile
import shutil
import unittest

from avocado.core import exit_codes
from avocado.core import test
from avocado.utils import process
from avocado.utils import script


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)

AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD", "./scripts/avocado")

INSTRUMENTED_SCRIPT = """import os
import tempfile
from avocado import Test
class MyTest(Test):
    def test1(self):
        tempfile.mkstemp(dir=self.teststmpdir)
        if len(os.listdir(self.teststmpdir)) != 2:
            self.fail()

"""

SIMPLE_SCRIPT = """#!/bin/bash
mktemp ${{{0}}}/XXXXXX
if [ $(ls ${{{0}}} | wc -l) == 1 ]
then
    exit 0
else
    exit 1
fi
""".format(test.COMMON_TMPDIR_NAME)


class TestsTmpDirTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.simple_test = script.TemporaryScript(
            'test_simple.sh',
            SIMPLE_SCRIPT)
        self.simple_test.save()
        self.instrumented_test = script.TemporaryScript(
            'test_instrumented.py',
            INSTRUMENTED_SCRIPT)
        self.instrumented_test.save()

    def run_and_check(self, cmd_line, expected_rc, env=None):
        os.chdir(basedir)
        result = process.run(cmd_line, ignore_status=True, env=env)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        return result

    @unittest.skipIf(test.COMMON_TMPDIR_NAME in os.environ,
                     "%s already set in os.environ"
                     % test.COMMON_TMPDIR_NAME)
    def test_tests_tmp_dir(self):
        """
        Tests whether automatically created teststmpdir is shared across
        all tests.
        """
        cmd_line = ("%s run --sysinfo=off "
                    "--job-results-dir %s %s %s"
                    % (AVOCADO, self.tmpdir, self.simple_test,
                       self.instrumented_test))
        self.run_and_check(cmd_line, exit_codes.AVOCADO_ALL_OK)

    def test_manualy_created(self):
        """
        Tests whether manually set teststmpdir is used and not deleted by
        avocado
        """
        shared_tmp = tempfile.mkdtemp(dir=self.tmpdir)
        cmd = ("%s run --sysinfo=off --job-results-dir %s %%s"
               % (AVOCADO, self.tmpdir))
        self.run_and_check(cmd % self.simple_test, exit_codes.AVOCADO_ALL_OK,
                           {test.COMMON_TMPDIR_NAME: shared_tmp})
        self.run_and_check(cmd % self.instrumented_test,
                           exit_codes.AVOCADO_ALL_OK,
                           {test.COMMON_TMPDIR_NAME: shared_tmp})
        content = os.listdir(shared_tmp)
        self.assertEqual(len(content), 2, "The number of tests in manually "
                         "set teststmpdir is not 2 (%s):\n%s"
                         % (len(content), content))

    def tearDown(self):
        self.instrumented_test.remove()
        self.simple_test.remove()
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
