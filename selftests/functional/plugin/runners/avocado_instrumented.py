from avocado import Test
from avocado.core.exit_codes import AVOCADO_JOB_INTERRUPTED
from avocado.utils import process
from selftests.utils import AVOCADO, TestCaseTmpDir


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
