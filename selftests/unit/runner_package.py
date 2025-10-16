import unittest
from multiprocessing import SimpleQueue
from unittest.mock import MagicMock, patch

from avocado.core.nrunner.runnable import Runnable
from avocado.plugins.runners.package import PackageRunner
from avocado.utils.software_manager.manager import SoftwareManager

SOFTWARE_MANAGER_CAPABLE = SoftwareManager().is_capable()


class BasicTests(unittest.TestCase):
    """Basic unit tests for the PackageRunner class"""

    def test_no_kwargs(self):
        runnable = Runnable(kind="package", uri=None)
        runner = PackageRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        result = "error"
        self.assertIn(result, messages[-1]["result"])
        stderr = b"Package name should be passed as kwargs"
        self.assertIn(stderr, messages[-2]["log"])

    def test_wrong_action(self):
        runnable = Runnable(kind="package", uri=None, **{"action": "foo"})
        runner = PackageRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        result = "error"
        self.assertIn(result, messages[-1]["result"])
        stderr = b"Invalid action foo. Use one of 'install', 'check' or 'remove'"
        self.assertIn(stderr, messages[-2]["log"])


@unittest.skipUnless(
    SOFTWARE_MANAGER_CAPABLE, "Not capable of a SoftwareManager backend"
)
class ActionTests(unittest.TestCase):
    """Unit tests for the actions on PackageRunner class

    Note: These tests directly call _run_software_manager to avoid
    multiprocessing issues with mocking. The multiprocessing behavior
    is tested in integration tests.
    """

    def test_success_install(self):
        with patch("avocado.plugins.runners.package.SoftwareManager") as mock_sm:
            mock_instance = MagicMock()
            mock_instance.is_capable.return_value = True
            mock_instance.check_installed.return_value = False
            mock_instance.install.return_value = True
            mock_sm.return_value = mock_instance

            runner = PackageRunner()
            queue = SimpleQueue()
            runner._run_software_manager("install", "foo", queue)

            output = queue.get()
            self.assertEqual(output["result"], "pass")
            self.assertIn("Package(s) foo installed successfully", output["stdout"])

    def test_already_installed(self):
        with patch("avocado.plugins.runners.package.SoftwareManager") as mock_sm:
            mock_instance = MagicMock()
            mock_instance.is_capable.return_value = True
            mock_instance.check_installed.return_value = True
            mock_sm.return_value = mock_instance

            runner = PackageRunner()
            queue = SimpleQueue()
            runner._run_software_manager("install", "foo", queue)

            output = queue.get()
            self.assertEqual(output["result"], "pass")
            self.assertIn("Package foo already installed", output["stdout"])

    def test_fail_install(self):
        with patch("avocado.plugins.runners.package.SoftwareManager") as mock_sm:
            mock_instance = MagicMock()
            mock_instance.is_capable.return_value = True
            mock_instance.check_installed.return_value = False
            mock_instance.install.return_value = False
            mock_sm.return_value = mock_instance

            runner = PackageRunner()
            queue = SimpleQueue()
            runner._run_software_manager("install", "foo", queue)

            output = queue.get()
            self.assertEqual(output["result"], "error")
            self.assertIn("Failed to install foo.", output["stderr"])

    def test_success_remove(self):
        with patch("avocado.plugins.runners.package.SoftwareManager") as mock_sm:
            mock_instance = MagicMock()
            mock_instance.is_capable.return_value = True
            mock_instance.check_installed.return_value = True
            mock_instance.remove.return_value = True
            mock_sm.return_value = mock_instance

            runner = PackageRunner()
            queue = SimpleQueue()
            runner._run_software_manager("remove", "foo", queue)

            output = queue.get()
            self.assertEqual(output["result"], "pass")
            self.assertIn("Package(s) foo removed successfully", output["stdout"])

    def test_not_installed(self):
        with patch("avocado.plugins.runners.package.SoftwareManager") as mock_sm:
            mock_instance = MagicMock()
            mock_instance.is_capable.return_value = True
            mock_instance.check_installed.return_value = False
            mock_sm.return_value = mock_instance

            runner = PackageRunner()
            queue = SimpleQueue()
            runner._run_software_manager("remove", "foo", queue)

            output = queue.get()
            self.assertEqual(output["result"], "pass")
            self.assertIn("Package foo not installed", output["stdout"])

    def test_fail_remove(self):
        with patch("avocado.plugins.runners.package.SoftwareManager") as mock_sm:
            mock_instance = MagicMock()
            mock_instance.is_capable.return_value = True
            mock_instance.check_installed.return_value = True
            mock_instance.remove.return_value = False
            mock_sm.return_value = mock_instance

            runner = PackageRunner()
            queue = SimpleQueue()
            runner._run_software_manager("remove", "foo", queue)

            output = queue.get()
            self.assertEqual(output["result"], "error")
            self.assertIn("Failed to remove foo.", output["stderr"])

    def test_success_check(self):
        with patch("avocado.plugins.runners.package.SoftwareManager") as mock_sm:
            mock_instance = MagicMock()
            mock_instance.is_capable.return_value = True
            mock_instance.check_installed.return_value = True
            mock_sm.return_value = mock_instance

            runner = PackageRunner()
            queue = SimpleQueue()
            runner._run_software_manager("check", "foo", queue)

            output = queue.get()
            self.assertEqual(output["result"], "pass")
            self.assertIn("Package foo already installed", output["stdout"])

    def test_fail_check(self):
        with patch("avocado.plugins.runners.package.SoftwareManager") as mock_sm:
            mock_instance = MagicMock()
            mock_instance.is_capable.return_value = True
            mock_instance.check_installed.return_value = False
            mock_sm.return_value = mock_instance

            runner = PackageRunner()
            queue = SimpleQueue()
            runner._run_software_manager("check", "foo", queue)

            output = queue.get()
            self.assertEqual(output["result"], "error")
            self.assertIn("Package foo not installed", output["stderr"])


if __name__ == "__main__":
    unittest.main()
