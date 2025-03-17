import os
import sys
import unittest

from avocado.utils import process
from selftests.utils import AVOCADO, TestCaseTmpDir, missing_binary

RUNNER = f"{sys.executable} -m avocado.plugins.runners.vmimage"


@unittest.skipIf(
    missing_binary("qemu-img"),
    "QEMU disk image utility is required by the vmimage utility ",
)
class VMImageTest(TestCaseTmpDir):
    def test_vmimage_dependencies(self):
        """Test that the vmimage dependency system correctly downloads and caches VM images."""
        test_path = "./examples/tests/dependency_vmimage.py"
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

        job_dir = os.path.join(self.tmpdir.name, "latest")
        log_path = os.path.join(
            job_dir,
            "test-results",
            "1-._examples_tests_dependency_vmimage.py_VmimageTest.test_vmimage",
            "debug.log",
        )

        self.assertTrue(
            os.path.exists(log_path), f"Debug log file not found at {log_path}"
        )

        with open(log_path, "r", encoding="utf-8") as f:
            log_content = f.read()

        self.assertIn(
            "VM image path:",
            log_content,
            "Could not find VM image path information in the log",
        )

    def test_vmimage_cli_with_all_params(self):
        """Test the vmimage runner using the command-line interface with all parameters."""
        res = process.run(
            f"{RUNNER} task-run -i vmimage_0 -k vmimage "
            "provider=Fedora version=41 arch=x86_64",
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
            f"{RUNNER} task-run -i vmimage_1 -k vmimage " "provider=Fedora",
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
            f"{RUNNER} runnable-run -k vmimage",
            ignore_status=True,
            shell=True,
        )
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'result': 'error'", res.stdout)
        self.assertEqual(res.exit_status, 0)


if __name__ == "__main__":
    unittest.main()
