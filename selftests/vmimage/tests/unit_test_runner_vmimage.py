import logging
import sys
import unittest

from avocado.core.nrunner.runnable import Runnable
from avocado.plugins.runners.vmimage import VMImageRunner
from avocado.utils import path
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
class VMImageRunnerTest(unittest.TestCase):
    def setUp(self):
        self.log = logging.getLogger("avocado.test")

    def test_vmimage_basic(self):
        """Test the vmimage runner using the Python API directly."""
        runnable = Runnable(
            "vmimage",
            "",
            kwargs={
                "provider": "Fedora",
                "version": "41",
                "arch": "x86_64",
            },
            config={"debug": True},
        )
        runner = VMImageRunner()
        try:
            print("Running vmimage runner...")
            results = [status for status in runner.run(runnable)]
            print(f"Results: {results}")
            for i, result in enumerate(results):
                print(f"Result {i}: {result}")
        except Exception as e:
            self.fail(f"Runner raised an exception: {str(e)}")

        self.assertEqual(results[0]["status"], "started")
        self.assertEqual(results[-1]["status"], "finished")

        # Print detailed information about the final result
        print(f"Final result: {results[-1]}")
        print(f"Result status: {results[-1].get('status')}")
        print(f"Result result: {results[-1].get('result')}")
        print(f"Result fail_reason: {results[-1].get('fail_reason')}")
        print(f"Result fail_class: {results[-1].get('fail_class')}")
        print(f"Result traceback: {results[-1].get('traceback')}")

        # The test should pass only if the image is downloaded successfully
        self.assertEqual(
            results[-1].get("result"),
            "pass",
            f"Test failed with error: {results[-1].get('fail_reason')}",
        )

    def test_missing_provider(self):
        """Test that the vmimage runner correctly handles missing provider parameter."""
        runnable = Runnable(
            "vmimage",
            "",
            kwargs={},
            config={"debug": True},
        )
        runner = VMImageRunner()
        results = [status for status in runner.run(runnable)]

        self.assertEqual(results[-1]["status"], "finished")
        self.assertEqual(results[-1]["result"], "error")

    def test_only_provider(self):
        """Test that the vmimage runner works with only the provider parameter."""
        runnable = Runnable(
            "vmimage",
            "",
            kwargs={
                "provider": "Fedora",
            },
            config={"debug": True},
        )
        runner = VMImageRunner()
        try:
            print("Running vmimage runner with only provider parameter...")
            results = [status for status in runner.run(runnable)]
            print(f"Results: {results}")
            for i, result in enumerate(results):
                print(f"Result {i}: {result}")
        except Exception as e:
            self.fail(f"Runner raised an exception: {str(e)}")

        self.assertEqual(results[0]["status"], "started")
        self.assertEqual(results[-1]["status"], "finished")

        # Print detailed information about the final result
        print(f"Final result: {results[-1]}")
        print(f"Result status: {results[-1].get('status')}")
        print(f"Result result: {results[-1].get('result')}")
        print(f"Result fail_reason: {results[-1].get('fail_reason')}")
        print(f"Result fail_class: {results[-1].get('fail_class')}")
        print(f"Result traceback: {results[-1].get('traceback')}")

        # The test should pass only if the image is downloaded successfully
        self.assertEqual(
            results[-1].get("result"),
            "pass",
            f"Test failed with error: {results[-1].get('fail_reason')}",
        )


if __name__ == "__main__":
    unittest.main()
