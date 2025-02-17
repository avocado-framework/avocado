import unittest.mock

import avocado.core.nrunner.runnable as runnable_mod
from avocado.core.nrunner.runnable import Runnable


class RunnableFromAPI(unittest.TestCase):
    def test_kind_noop(self):
        runnable = Runnable("noop", None)
        self.assertEqual(runnable.kind, "noop")
        self.assertEqual(runnable.uri, None)

    def test_kind_required(self):
        self.assertRaises(TypeError, Runnable)

    def test_args(self):
        runnable = Runnable("noop", None, "arg1", "arg2")
        self.assertIn("arg1", runnable.args)
        self.assertIn("arg2", runnable.args)
        self.assertEqual(len(runnable.args), 2)

    def test_kwargs(self):
        runnable = Runnable("noop", "uri", key1="val1", key2="val2")
        self.assertEqual(runnable.kwargs.get("key1"), "val1")
        self.assertEqual(runnable.kwargs.get("key2"), "val2")

    def test_args_kwargs(self):
        runnable = Runnable("noop", "uri", "arg1", "arg2", key1="val1", key2="val2")
        self.assertIn("arg1", runnable.args)
        self.assertIn("arg2", runnable.args)
        self.assertEqual(runnable.kwargs.get("key1"), "val1")
        self.assertEqual(runnable.kwargs.get("key2"), "val2")

    def test_tags(self):
        runnable = Runnable("noop", "uri", tags={"arch": set(["x86_64", "ppc64"])})
        self.assertIn("x86_64", runnable.tags.get("arch"))
        self.assertIn("ppc64", runnable.tags.get("arch"))

    def test_args_kwargs_tags(self):
        runnable = Runnable(
            "noop",
            "uri",
            "arg1",
            "arg2",
            tags={"arch": set(["x86_64", "ppc64"])},
            non_standard_option="non_standard_value",
        )
        self.assertIn("arg1", runnable.args)
        self.assertIn("arg2", runnable.args)
        self.assertIn("x86_64", runnable.tags.get("arch"))
        self.assertIn("ppc64", runnable.tags.get("arch"))
        self.assertEqual(
            runnable.kwargs.get("non_standard_option"), "non_standard_value"
        )

    def test_identifier_args(self):
        config = {"runner.identifier_format": "{uri}-{args[0]}"}
        runnable = Runnable("exec-test", "uri", "arg1", "arg2", config=config)
        self.assertEqual(runnable.identifier, "uri-arg1")

    def test_command_args(self):
        runnable = Runnable("noop", "uri", "arg1", "arg2")
        actual_args = runnable.get_command_args()
        exp_args = [
            "-k",
            "noop",
            "-u",
            "uri",
            "-c",
            '{"runner.identifier_format": "{uri}"}',
            "-a",
            "arg1",
            "-a",
            "arg2",
        ]
        self.assertEqual(actual_args, exp_args)

    def test_get_dict(self):
        runnable = Runnable("noop", "_uri_", "arg1", "arg2")
        self.assertEqual(
            runnable.get_dict(),
            {
                "kind": "noop",
                "uri": "_uri_",
                "args": ("arg1", "arg2"),
                "config": {"runner.identifier_format": "{uri}"},
                "identifier": "_uri_",
            },
        )

    def test_get_json(self):
        runnable = Runnable("noop", "_uri_", "arg1", "arg2")
        expected = (
            '{"kind": "noop", '
            '"uri": "_uri_", '
            '"config": {"runner.identifier_format": "{uri}"}, '
            '"identifier": "_uri_", '
            '"args": ["arg1", "arg2"]}'
        )
        self.assertEqual(runnable.get_json(), expected)

    def test_runner_from_runnable_error(self):
        try:
            runnable = Runnable("unsupported_kind", "")
            runnable.pick_runner_class()
        except ValueError as e:
            self.assertEqual(str(e), "Unsupported kind of runnable: unsupported_kind")


class RunnableFromRecipe(unittest.TestCase):
    def test(self):
        open_mocked = unittest.mock.mock_open(read_data='{"kind": "noop"}')
        with unittest.mock.patch("avocado.core.nrunner.runnable.open", open_mocked):
            runnable = Runnable.from_recipe("fake_path")
        self.assertEqual(runnable.kind, "noop")

    def test_exec(self):
        open_mocked = unittest.mock.mock_open(
            read_data=(
                '{"kind": "exec-test", "uri": "/bin/sh", '
                '"args": ["/etc/profile"], '
                '"kwargs": {"TERM": "vt3270"}}'
            )
        )
        with unittest.mock.patch("avocado.core.nrunner.runnable.open", open_mocked):
            runnable = Runnable.from_recipe("fake_path")
        self.assertEqual(runnable.kind, "exec-test")
        self.assertEqual(runnable.uri, "/bin/sh")
        self.assertEqual(runnable.args, ("/etc/profile",))
        self.assertEqual(runnable.kwargs, {"TERM": "vt3270"})

    def test_config(self):
        open_mocked = unittest.mock.mock_open(
            read_data=(
                '{"kind": "exec-test", "uri": "/bin/sh", '
                '"args": ["/etc/profile"], '
                '"config": {"runner.identifier_format": "{uri}-{args[0]}"}}'
            )
        )
        with unittest.mock.patch("avocado.core.nrunner.runnable.open", open_mocked):
            runnable = Runnable.from_recipe("fake_path")
        configuration_used = ["run.keep_tmp", "runner.exectest.exitcodes.skip"]
        for conf in configuration_used:
            self.assertIn(conf, runnable.config)
        self.assertEqual(
            runnable.config.get("runner.identifier_format"), "{uri}-{args[0]}"
        )

    def test_config_at_init(self):
        runnable = Runnable("exec-test", "/bin/sh")
        self.assertEqual(
            set(runnable.config.keys()),
            set(
                [
                    "run.keep_tmp",
                    "runner.exectest.exitcodes.skip",
                    "runner.exectest.clear_env",
                    "runner.identifier_format",
                ]
            ),
        )

    def test_config_warn_if_not_used(self):
        runnable = Runnable("exec-test", "/bin/sh")
        with unittest.mock.patch.object(runnable_mod.LOG, "warning") as log_mock:
            runnable.config = {"some-unused-config": "foo"}
        log_mock.assert_called_once()

    def test_config_dont_warn_if_used(self):
        with unittest.mock.patch.object(runnable_mod.LOG, "warning") as log_mock:
            Runnable("noop", "noop", config={"runner.identifier_format": "noop"})
        log_mock.assert_not_called()

    def test_default_config(self):
        runnable = Runnable("noop", "noop")
        self.assertEqual(
            runnable.default_config.get("runner.identifier_format"), "{uri}"
        )

    def test_default_and_actual_config(self):
        runnable = Runnable("noop", "noop", config={"runner.identifier_format": "noop"})
        self.assertEqual(runnable.config.get("runner.identifier_format"), "noop")
        self.assertEqual(
            runnable.default_config.get("runner.identifier_format"), "{uri}"
        )

    def test_identifier(self):
        open_mocked = unittest.mock.mock_open(
            read_data=(
                '{"kind": "exec-test", "uri": "/bin/sh", '
                '"args": ["/etc/profile"], '
                '"config": {"runner.identifier_format": "{uri}-{args[0]}"}, '
                '"identifier": "exec-test-1"}'
            )
        )
        with unittest.mock.patch("avocado.core.nrunner.runnable.open", open_mocked):
            runnable = Runnable.from_recipe("fake_path")
        self.assertEqual(runnable.identifier, "exec-test-1")


class RunnableFromCommandLineArgs(unittest.TestCase):
    def test_noop(self):
        parsed_args = {"kind": "noop", "uri": None}
        runnable = Runnable.from_args(parsed_args)
        self.assertEqual(runnable.kind, "noop")
        self.assertIsNone(runnable.uri)

    def test_exec_args(self):
        parsed_args = {
            "kind": "exec-test",
            "uri": "/path/to/executable",
            "arg": ["-a", "-b", "-c"],
        }
        runnable = Runnable.from_args(parsed_args)
        self.assertEqual(runnable.kind, "exec-test")
        self.assertEqual(runnable.uri, "/path/to/executable")
        self.assertEqual(runnable.args, ("-a", "-b", "-c"))
        self.assertEqual(runnable.kwargs, {})

    def test_exec_args_kwargs(self):
        parsed_args = {
            "kind": "exec-test",
            "uri": "/path/to/executable",
            "arg": ["-a", "-b", "-c"],
            "kwargs": [("DEBUG", "1"), ("LC_ALL", "C")],
        }
        runnable = Runnable.from_args(parsed_args)
        self.assertEqual(runnable.kind, "exec-test")
        self.assertEqual(runnable.uri, "/path/to/executable")
        self.assertEqual(runnable.args, ("-a", "-b", "-c"))
        self.assertEqual(runnable.kwargs.get("DEBUG"), "1")
        self.assertEqual(runnable.kwargs.get("LC_ALL"), "C")

    def test_kwargs_json_empty_dict(self):
        parsed_args = {"kind": "noop", "uri": None, "kwargs": [("empty", "json:{}")]}
        runnable = Runnable.from_args(parsed_args)
        self.assertEqual(runnable.kind, "noop")
        self.assertIsNone(runnable.uri)
        self.assertEqual(runnable.kwargs.get("empty"), {})

    def test_kwargs_json_dict(self):
        parsed_args = {
            "kind": "noop",
            "uri": None,
            "kwargs": [
                ("tags", 'json:{"arch": ["x86_64", "ppc64"]}'),
                ("hi", 'json:"hello"'),
            ],
        }
        runnable = Runnable.from_args(parsed_args)
        self.assertEqual(runnable.kind, "noop")
        self.assertIsNone(runnable.uri)
        self.assertEqual(runnable.kwargs.get("hi"), "hello")
        self.assertEqual(runnable.tags.get("arch"), ["x86_64", "ppc64"])


class RunnableToRecipe(unittest.TestCase):
    def test_runnable_to_recipe_noop(self):
        runnable = Runnable("noop", None)
        open_mocked = unittest.mock.mock_open(read_data=runnable.get_json())
        with unittest.mock.patch("avocado.core.nrunner.runnable.open", open_mocked):
            loaded_runnable = Runnable.from_recipe("fake_path")
        self.assertEqual(loaded_runnable.kind, "noop")

    def test_runnable_to_recipe_uri(self):
        runnable = Runnable("exec-test", "/bin/true")
        open_mocked = unittest.mock.mock_open(read_data=runnable.get_json())
        with unittest.mock.patch("avocado.core.nrunner.runnable.open", open_mocked):
            loaded_runnable = Runnable.from_recipe("fake_path")
        self.assertEqual(loaded_runnable.kind, "exec-test")
        self.assertEqual(loaded_runnable.uri, "/bin/true")

    def test_runnable_to_recipe_args(self):
        runnable = Runnable("exec-test", "/bin/sleep", "0.01", identifier="exec-test-1")
        open_mocked = unittest.mock.mock_open(read_data=runnable.get_json())
        with unittest.mock.patch("avocado.core.nrunner.runnable.open", open_mocked):
            loaded_runnable = Runnable.from_recipe("fake_path")
        self.assertEqual(loaded_runnable.kind, "exec-test")
        self.assertEqual(loaded_runnable.uri, "/bin/sleep")
        self.assertEqual(loaded_runnable.args, ("0.01",))
        self.assertEqual(loaded_runnable.identifier, "exec-test-1")
