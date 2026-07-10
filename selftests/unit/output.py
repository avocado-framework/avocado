import sys
import types
import unittest.mock
from importlib.metadata import EntryPoint

from avocado.core import output
from avocado.utils import path as utils_path


class TestStdOutput(unittest.TestCase):
    def setUp(self):
        """Preserve sys.std{out,err} so we can restore them in tearDown"""
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def tearDown(self):
        sys.stdout = self.stdout
        sys.stderr = self.stderr

    def test_paginator_not_available(self):
        """Check that without paginator command we proceed without changes"""
        std = output.StdOutput()
        with unittest.mock.patch(
            "avocado.utils.path.find_command",
            side_effect=utils_path.CmdNotFoundError("just", ["mocking"]),
        ):
            std.enable_paginator()
        self.assertEqual(self.stdout, sys.stdout)
        self.assertEqual(self.stderr, sys.stderr)


class TestLogPluginFailures(unittest.TestCase):
    @staticmethod
    def _raised_import_error():
        try:
            raise ImportError("broken plugin with traceback")
        except ImportError as exception:
            return exception

    @staticmethod
    def _log_plugin_failure(entry_point, exception=None, silenced=None):
        config = {"plugins.skip_broken_plugin_notification": silenced or []}
        if exception is None:
            exception = ImportError("broken plugin")
        with unittest.mock.patch.object(
            output.settings, "as_dict", return_value=config
        ), unittest.mock.patch.object(output.LOG_UI, "error") as log_error:
            output.log_plugin_failures([(entry_point, exception)])
        return log_error

    def test_importlib_entry_point(self):
        entry_point = EntryPoint(
            name="vt",
            value="avocado_vt.plugins.vt:VTCli",
            group="avocado.plugins.cli",
        )

        log_error = self._log_plugin_failure(entry_point)

        log_error.assert_called_once()
        self.assertEqual(log_error.call_args[0][1], "avocado_vt.plugins.vt")

    def test_pkg_resources_entry_point(self):
        entry_point = types.SimpleNamespace(module_name="avocado.plugins.jobs")

        log_error = self._log_plugin_failure(entry_point)

        log_error.assert_called_once()
        self.assertEqual(log_error.call_args[0][1], "avocado.plugins.jobs")

    def test_entry_point_value_fallback(self):
        entry_point = types.SimpleNamespace(
            value="avocado.plugins.legacy:LegacyPlugin [extra]"
        )

        log_error = self._log_plugin_failure(entry_point)

        log_error.assert_called_once()
        self.assertEqual(log_error.call_args[0][1], "avocado.plugins.legacy")

    def test_entry_point_value_fallback_with_extras(self):
        entry_point = types.SimpleNamespace(value="avocado.plugins.legacy [extra]")

        log_error = self._log_plugin_failure(entry_point)

        log_error.assert_called_once()
        self.assertEqual(log_error.call_args[0][1], "avocado.plugins.legacy")

    def test_traceback_is_logged_for_plugin_failure(self):
        entry_point = EntryPoint(
            name="vt",
            value="avocado_vt.plugins.vt:VTCli",
            group="avocado.plugins.cli",
        )
        exception = self._raised_import_error()

        log_error = self._log_plugin_failure(entry_point, exception=exception)

        log_error.assert_called_once()
        logged_traceback = log_error.call_args[0][3]
        self.assertIn("_raised_import_error", logged_traceback)
        self.assertIn(
            'raise ImportError("broken plugin with traceback")', logged_traceback
        )

    def test_silenced_importlib_entry_point(self):
        entry_point = EntryPoint(
            name="vt",
            value="avocado_vt.plugins.vt:VTCli",
            group="avocado.plugins.cli",
        )

        log_error = self._log_plugin_failure(
            entry_point, silenced=["avocado_vt.plugins.vt"]
        )

        log_error.assert_not_called()

    def test_silenced_pkg_resources_entry_point(self):
        entry_point = types.SimpleNamespace(module_name="avocado.plugins.jobs")

        log_error = self._log_plugin_failure(
            entry_point, silenced=["avocado.plugins.jobs"]
        )

        log_error.assert_not_called()


if __name__ == "__main__":
    unittest.main()
