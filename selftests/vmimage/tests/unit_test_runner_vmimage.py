import sys
import unittest

from avocado.core.nrunner.runnable import Runnable
from avocado.plugins.runners.vmimage import VMImageRunner
from selftests.utils import missing_binary

RUNNER = f"{sys.executable} -m avocado.plugins.runners.vmimage"


@unittest.skipIf(
    missing_binary("qemu-img"),
    "QEMU disk image utility is required by the vmimage utility ",
)
class VMImageRunnerTest(unittest.TestCase):
    def test_vmimage_basic(self):
        """Test the vmimage runner using the Python API directly."""

        kwargs = {
            "provider": "Fedora",
            "version": "41",
            "arch": "x86_64",
        }
        runnable = Runnable("vmimage", "", config={}, **kwargs)
        runner = VMImageRunner()
        try:
            results = [status for status in runner.run(runnable)]
        except Exception as e:
            self.fail(f"Runner raised an exception: {str(e)}")

        self.assertEqual(
            results[0]["status"], "started", "Runner did not report 'started' status"
        )
        self.assertEqual(
            results[-1]["status"], "finished", "Runner did not report 'finished' status"
        )

        # The test should pass only if the image is downloaded successfully
        self.assertEqual(
            results[-1].get("result"),
            "pass",
            f"Test failed with error: {results[-1].get('fail_reason')}",
        )

    def test_missing_provider(self):
        """Test that the vmimage runner correctly handles missing provider parameter."""
        kwargs = {}
        runnable = Runnable("vmimage", "", config={}, **kwargs)
        runner = VMImageRunner()
        results = [status for status in runner.run(runnable)]

        self.assertEqual(
            results[-1]["status"], "finished", "Runner did not report 'finished' status"
        )
        self.assertEqual(
            results[-1]["result"],
            "error",
            "Runner did not report 'error' result for missing provider",
        )

    def test_only_provider(self):
        """Test that the vmimage runner works with only the provider parameter."""
        kwargs = {
            "provider": "Fedora",
        }
        runnable = Runnable("vmimage", "", config={}, **kwargs)
        runner = VMImageRunner()
        try:
            results = [status for status in runner.run(runnable)]
        except Exception as e:
            self.fail(f"Runner raised an exception: {str(e)}")

        self.assertEqual(
            results[0]["status"], "started", "Runner did not report 'started' status"
        )
        self.assertEqual(
            results[-1]["status"], "finished", "Runner did not report 'finished' status"
        )

        # The test should pass only if the image is downloaded successfully
        self.assertEqual(
            results[-1].get("result"),
            "pass",
            f"Test failed with error: {results[-1].get('fail_reason')}",
        )


if __name__ == "__main__":
    unittest.main()
