import re
from os import path

import yaml

from avocado.utils import process
from selftests.utils import AVOCADO, TestCaseTmpDir


class TMTResultTest(TestCaseTmpDir):
    def test_logfile(self):
        cmd_line = (
            f"{AVOCADO} run examples/tests/failtest.py examples/tests/passtest.py"
            f" --job-results-dir {self.tmpdir.name} --disable-sysinfo --max-parallel-tasks=1"
        )
        result = process.run(cmd_line, ignore_status=True)
        regex = re.search(r"JOB LOG.*: (\S*)", result.stdout_text)
        job_path = path.dirname(regex.group(1))
        tmt_path = path.join(job_path, "results.yaml")

        with open(tmt_path, "r", encoding="utf-8") as tmt_file:
            data = yaml.safe_load(tmt_file)
            self.assertEqual(len(data), 2)
            failtest_data = data[0]
            self.assertEqual(
                failtest_data["name"], "/1-examples/tests/failtest.py:FailTest.test"
            )
            self.assertEqual(failtest_data["result"], "fail")
            self.assertEqual(failtest_data["data-path"], job_path)
            self.assertEqual(
                failtest_data["log"][0],
                path.join(
                    "test-results",
                    "1-examples_tests_failtest.py_FailTest.test",
                    "debug.log",
                ),
            )
            passtest_data = data[1]
            self.assertEqual(
                passtest_data["name"], "/2-examples/tests/passtest.py:PassTest.test"
            )
            self.assertEqual(passtest_data["result"], "pass")
            self.assertEqual(passtest_data["data-path"], job_path)
            self.assertEqual(
                passtest_data["log"][0],
                path.join(
                    "test-results",
                    "2-examples_tests_passtest.py_PassTest.test",
                    "debug.log",
                ),
            )
