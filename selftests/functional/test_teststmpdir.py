import os
import tempfile
import unittest

from avocado.core import exit_codes, test
from avocado.utils import process, script
from selftests.utils import AVOCADO, TestCaseTmpDir

INSTRUMENTED_SCRIPT = """import os
import tempfile
from avocado import Test
class MyTest(Test):
    def test1(self):
        tempfile.mkstemp(dir=self.teststmpdir)
        if len(os.listdir(self.teststmpdir)) != 2:
            self.fail()

"""

SIMPLE_SCRIPT = (f"""#!/bin/bash
mktemp ${{{test.COMMON_TMPDIR_NAME}}}/XXXXXX
if [ $(ls ${{{test.COMMON_TMPDIR_NAME}}} | wc -l) == 1 ]
then
    exit 0
else
    exit 1
fi
""")


class TestsTmpDirTests(TestCaseTmpDir):

    def setUp(self):
        super().setUp()
        self.simple_test = script.TemporaryScript(
            'test_simple.sh',
            SIMPLE_SCRIPT)
        self.simple_test.save()
        self.instrumented_test = script.TemporaryScript(
            'test_instrumented.py',
            INSTRUMENTED_SCRIPT)
        self.instrumented_test.save()

    def run_and_check(self, cmd_line, expected_rc, env=None):
        result = process.run(cmd_line, ignore_status=True, env=env)
        self.assertEqual(result.exit_status, expected_rc,
                         (f"Command {cmd_line} did not return rc "
                          f"{expected_rc}:\n{result}"))
        return result

    @unittest.skipIf(test.COMMON_TMPDIR_NAME in os.environ,
                     f"{test.COMMON_TMPDIR_NAME} already set in os.environ")
    def test_tests_tmp_dir(self):
        """
        Tests whether automatically created teststmpdir is shared across
        all tests.
        """
        cmd_line = (f"{AVOCADO} run --disable-sysinfo "
                    f"--job-results-dir {self.tmpdir.name} "
                    f"{self.simple_test} {self.instrumented_test}")
        self.run_and_check(cmd_line, exit_codes.AVOCADO_ALL_OK)

    def test_manualy_created(self):
        """
        Tests whether manually set teststmpdir is used and not deleted by
        avocado
        """
        with tempfile.TemporaryDirectory(dir=self.tmpdir.name) as shared_tmp:
            cmd = (f"{AVOCADO} run --disable-sysinfo "
                   f"--job-results-dir {self.tmpdir.name} %s")
            self.run_and_check(cmd % self.simple_test, exit_codes.AVOCADO_ALL_OK,
                               {test.COMMON_TMPDIR_NAME: shared_tmp})
            self.run_and_check(cmd % self.instrumented_test,
                               exit_codes.AVOCADO_ALL_OK,
                               {test.COMMON_TMPDIR_NAME: shared_tmp})
            content = os.listdir(shared_tmp)
            self.assertEqual(len(content), 2,
                             (f"The number of tests in manually set teststmpdir "
                              f"is not 2 ({len(content)}):\n{content}"))

    def tearDown(self):
        super().tearDown()
        self.instrumented_test.remove()
        self.simple_test.remove()


if __name__ == '__main__':
    unittest.main()
