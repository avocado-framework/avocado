import os
import sys
import unittest

from avocado.utils import path, process
from selftests.utils import AVOCADO, BASEDIR, TestCaseTmpDir
from selftests.vmimage.tests.utils.network import is_network_available

RUNNER = f"{sys.executable} -m avocado.plugins.runners.vmimage"


def missing_binary(binary):
    try:
        path.find_command(binary)
        return False
    except path.CmdNotFoundError:
        return True


@unittest.skipUnless(
    is_network_available(),
    "Network connectivity required to run these tests",
)
@unittest.skipIf(
    missing_binary("qemu-img"),
    "QEMU disk image utility is required by the vmimage utility ",
)
class VMImageTest(TestCaseTmpDir):
    def test_vmimage_dependencies(self):
        """Test that the vmimage dependency system correctly downloads and caches VM images."""
        test_path = os.path.join(
            BASEDIR,
            "selftests",
            "vmimage",
            "tests",
            "functional_dependency_vmimage.py",
        )
        cmd = f"{AVOCADO} run --job-results-dir '{self.tmpdir.name}' '{test_path}'"

        res = process.run(cmd, ignore_status=True, shell=True)

        self.assertEqual(
            res.exit_status,
            0,
            f"Command failed with exit {res.exit_status}. Stderr: {res.stderr}",
        )

        self.assertIn(
            b"RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0",
            res.stdout,
            f"Unexpected test results. Full stdout: {res.stdout}",
        )

        # Check logs to verify images were downloaded
        log_dir = os.path.join(self.tmpdir.name, "latest", "test-results")
        found_logs = False

        # Walk through the log directory to find test logs
        for root, _, files in os.walk(log_dir):
            for log_file in files:
                if log_file == "debug.log":
                    log_path = os.path.join(root, log_file)
                    with open(log_path, "r", encoding="utf-8") as f:
                        log_content = f.read()

                        # Check for evidence that vmimage.get was used and images were found
                        if "VM image path:" in log_content:
                            found_logs = True
                            # Our functional_dependency_vmimage.py only uses Fedora 41 x86_64
                            self.assertIn("VM image path:", log_content)
                            break

            if found_logs:
                break

        self.assertTrue(
            found_logs, "Could not find test logs with image path information"
        )

    def test_vmimage_cli_with_all_params(self):
        """Test the vmimage runner using the command-line interface with all parameters."""
        res = process.run(
            f"{RUNNER} task-run -i vmimage_0 -k vmimage "
            "provider=Fedora version=41 arch=x86_64 debug=true",
            ignore_status=True,
            shell=True,
        )
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'result': 'pass'", res.stdout)
        self.assertEqual(res.exit_status, 0)

    def test_vmimage_cli_with_only_provider(self):
        """Test the vmimage runner using the command-line interface with only provider parameter."""
        res = process.run(
            f"{RUNNER} task-run -i vmimage_1 -k vmimage " "provider=Fedora debug=true",
            ignore_status=True,
            shell=True,
        )
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'result': 'pass'", res.stdout)
        self.assertEqual(res.exit_status, 0)

    def test_missing_required_params(self):
        """Test that running without required parameters results in an error."""
        res = process.run(
            f"{RUNNER} runnable-run -k vmimage debug=true",
            ignore_status=True,
            shell=True,
        )
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'result': 'error'", res.stdout)
        self.assertEqual(res.exit_status, 0)


if __name__ == "__main__":
    unittest.main()
