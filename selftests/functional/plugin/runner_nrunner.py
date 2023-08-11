from avocado.core.exit_codes import AVOCADO_ALL_OK
from avocado.utils import process
from selftests.utils import AVOCADO, TestCaseTmpDir


class NrunnerTest(TestCaseTmpDir):
    def test_status_server_uri(self):
        result = process.run(
            f"{AVOCADO} run "
            f"--job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo --status-server-disable-auto "
            f"--status-server-uri 127.0.0.1:9999 "
            f"examples/tests/true",
        )
        self.assertIn("PASS 1 ", result.stdout_text)
        self.assertEqual(result.exit_status, AVOCADO_ALL_OK)
