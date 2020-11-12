import os

from avocado.core import exit_codes
from avocado.utils import process

from .. import AVOCADO, TestCaseTmpDir

CONFIG = """[job.output.testlogs]
statuses = ["FAIL", "CANCEL"]"""


class TestLogs(TestCaseTmpDir):

    def setUp(self):
        super(TestLogs, self).setUp()
        with open(os.path.join(self.tmpdir.name, 'config'), 'w') as config:
            config.write(CONFIG)

    def test(self):
        cmd_line = ("%s --config=%s run -- examples/tests/passtest.py "
                    "examples/tests/failtest.py examples/tests/canceltest.py ")
        cmd_line %= (AVOCADO, os.path.join(self.tmpdir.name, 'config'))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_TESTS_FAIL,
                         "Avocado did not return rc %d:\n%s"
                         % (exit_codes.AVOCADO_ALL_OK, result))
        stdout_lines = result.stdout_text.splitlines()
        self.assertNotIn('Log content for test "1-examples/tests/passtest.py'
                         ':PassTest.test" (PASS)', stdout_lines)
        self.assertIn('Log content for test "2-examples/tests/failtest.py:'
                      'FailTest.test" (FAIL)', stdout_lines)
        self.assertIn('Log content for test "3-examples/tests/canceltest.py'
                      ':CancelTest.test" (CANCEL)', stdout_lines)
