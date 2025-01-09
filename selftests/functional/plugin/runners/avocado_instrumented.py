import json
import os

from avocado import Test
from avocado.core.exit_codes import AVOCADO_JOB_INTERRUPTED
from avocado.utils import process, script
from selftests.utils import AVOCADO, TestCaseTmpDir

TIMEOU_TEST_WITH_EXCEPTION = """
import time

from avocado import Test

class TimeoutTest(Test):

    timeout = 3

    def test(self):
        try:
            time.sleep(5)
        except Exception:
            pass

    def tearDown(self):
        self.log.info("TearDown")
"""


class AvocadoInstrumentedRunnerTest(TestCaseTmpDir, Test):
    def test_timeout(self):
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"-- examples/tests/timeouttest.py "
        )
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, AVOCADO_JOB_INTERRUPTED)
        self.assertIn(
            "examples/tests/timeouttest.py:TimeoutTest.test:  INTERRUPTED: Test interrupted: Timeout reached",
            result.stdout_text,
        )

    def test_timeout_with_exception(self):
        with script.TemporaryScript(
            "test_timeout.py",
            TIMEOU_TEST_WITH_EXCEPTION,
            "avocado_timeout_test",
        ) as tst:
            res = process.run(
                (
                    f"{AVOCADO} run --disable-sysinfo "
                    f"--job-results-dir {self.tmpdir.name} {tst} "
                    f"--json -"
                ),
                ignore_status=True,
            )
            results = json.loads(res.stdout_text)
            self.assertIn(
                "Test interrupted: Timeout reached",
                results["tests"][0]["fail_reason"],
            )
            debug_log_path = results["tests"][0]["logfile"]
            self.assertTrue(os.path.exists(debug_log_path))
            with open(debug_log_path, encoding="utf-8") as file:
                self.assertIn(
                    "INFO | TearDown",
                    file.read(),
                )
