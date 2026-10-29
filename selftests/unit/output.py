import logging
import os
import sys
import tempfile
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


class TestLogConfiguration(unittest.TestCase):
    def setUp(self):
        self.original_config = output.CONFIG
        output.CONFIG = [{}]
        self.logger = logging.getLogger(f"avocado.test.buffered.{id(self)}")
        self.original_handlers = list(self.logger.handlers)
        self.original_level = self.logger.level
        self.original_propagate = self.logger.propagate
        self.logger.handlers = []
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def tearDown(self):
        for handler in self.logger.handlers:
            handler.close()
        self.logger.handlers = self.original_handlers
        self.logger.setLevel(self.original_level)
        self.logger.propagate = self.original_propagate
        output.CONFIG = self.original_config

    def test_configured_level_filters_records_before_buffering(self):
        handler = output.add_log_handler(
            self.logger,
            logging.FileHandler,
            os.path.join(self.tmpdir.name, "level.log"),
            level=logging.INFO,
            buffer_size=1000,
        )
        self.addCleanup(handler.target.close)
        self.addCleanup(handler.close)
        self.logger.debug("record below configured level")
        self.assertEqual(handler.buffer, [])
        self.logger.info("record at configured level")
        self.assertEqual(
            [record.getMessage() for record in handler.buffer],
            ["record at configured level"],
        )

    def test_removing_configuration_flushes_buffered_file_handler(self):
        output.CONFIG.append({})
        log_path = os.path.join(self.tmpdir.name, "buffered.log")
        handler = output.add_log_handler(
            self.logger,
            logging.FileHandler,
            log_path,
            buffer_size=1000,
        )
        target = handler.target
        self.addCleanup(target.close)
        self.addCleanup(handler.close)
        self.logger.info("record waiting in memory")

        self.assertEqual(os.path.getsize(log_path), 0)

        output.del_last_configuration()

        with open(log_path, encoding="utf-8") as log_file:
            self.assertIn("record waiting in memory", log_file.read())
        self.assertNotIn(handler, self.logger.handlers)
        self.assertEqual(handler.buffer, [])
        self.assertIsNone(handler.target)
        self.assertFalse(target.stream.closed)


if __name__ == "__main__":
    unittest.main()
