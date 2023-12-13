import os
import sys
import tempfile
import unittest.mock

from avocado.core.nrunner.runnable import Runnable
from avocado.core.nrunner.task import Task
from avocado.plugins.runners import tap as runner_tap
from selftests.utils import skipUnlessPathExists, temp_dir_prefix


class RunnableTest(unittest.TestCase):
    def test_runnable_args(self):
        runnable = Runnable("noop", "uri", "arg1", "arg2")
        self.assertIn("arg1", runnable.args)
        self.assertIn("arg2", runnable.args)

    def test_runnable_kwargs(self):
        runnable = Runnable("noop", "uri", key1="val1", key2="val2")
        self.assertEqual(runnable.kwargs.get("key1"), "val1")
        self.assertEqual(runnable.kwargs.get("key2"), "val2")

    def test_runnable_args_kwargs(self):
        runnable = Runnable("noop", "uri", "arg1", "arg2", key1="val1", key2="val2")
        self.assertIn("arg1", runnable.args)
        self.assertIn("arg2", runnable.args)
        self.assertEqual(runnable.kwargs.get("key1"), "val1")
        self.assertEqual(runnable.kwargs.get("key2"), "val2")

    def test_runnable_tags(self):
        runnable = Runnable("noop", "uri", tags={"arch": set(["x86_64", "ppc64"])})
        self.assertIn("x86_64", runnable.tags.get("arch"))
        self.assertIn("ppc64", runnable.tags.get("arch"))

    def test_runnable_args_kwargs_tags(self):
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

    def test_kind_required(self):
        self.assertRaises(TypeError, Runnable)

    def test_kind_noop(self):
        runnable = Runnable("noop", None)
        self.assertEqual(runnable.kind, "noop")

    def test_recipe_noop(self):
        open_mocked = unittest.mock.mock_open(read_data='{"kind": "noop"}')
        with unittest.mock.patch("builtins.open", open_mocked):
            runnable = Runnable.from_recipe("fake_path")
        self.assertEqual(runnable.kind, "noop")

    def test_recipe_exec(self):
        open_mocked = unittest.mock.mock_open(
            read_data=(
                '{"kind": "exec-test", "uri": "/bin/sh", '
                '"args": ["/etc/profile"], '
                '"kwargs": {"TERM": "vt3270"}}'
            )
        )
        with unittest.mock.patch("builtins.open", open_mocked):
            runnable = Runnable.from_recipe("fake_path")
        self.assertEqual(runnable.kind, "exec-test")
        self.assertEqual(runnable.uri, "/bin/sh")
        self.assertEqual(runnable.args, ("/etc/profile",))
        self.assertEqual(runnable.kwargs, {"TERM": "vt3270"})

    def test_identifier_args(self):
        config = {"runner.identifier_format": "{uri}-{args[0]}"}
        runnable = Runnable("exec-test", "uri", "arg1", "arg2", config=config)
        self.assertEqual(runnable.identifier, "uri-arg1")

    def test_runnable_command_args(self):
        runnable = Runnable("noop", "uri", "arg1", "arg2")
        actual_args = runnable.get_command_args()
        exp_args = ["-k", "noop", "-u", "uri", "-a", "arg1", "-a", "arg2"]
        self.assertEqual(actual_args, exp_args)

    def test_get_dict(self):
        runnable = Runnable("noop", "_uri_", "arg1", "arg2")
        self.assertEqual(
            runnable.get_dict(),
            {"kind": "noop", "uri": "_uri_", "args": ("arg1", "arg2"), "config": {}},
        )

    def test_get_json(self):
        runnable = Runnable("noop", "_uri_", "arg1", "arg2")
        expected = (
            '{"kind": "noop", '
            '"uri": "_uri_", '
            '"config": {}, '
            '"args": ["arg1", "arg2"]}'
        )
        self.assertEqual(runnable.get_json(), expected)

    def test_runner_from_runnable_error(self):
        try:
            runnable = Runnable("unsupported_kind", "")
            runnable.pick_runner_class()
        except ValueError as e:
            self.assertEqual(str(e), "Unsupported kind of runnable: unsupported_kind")


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
    def setUp(self):
        prefix = temp_dir_prefix(self)
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    def test_runnable_to_recipe_noop(self):
        runnable = Runnable("noop", None)
        recipe_path = os.path.join(self.tmpdir.name, "recipe.json")
        runnable.write_json(recipe_path)
        self.assertTrue(os.path.exists(recipe_path))
        loaded_runnable = Runnable.from_recipe(recipe_path)
        self.assertEqual(loaded_runnable.kind, "noop")

    def test_runnable_to_recipe_uri(self):
        runnable = Runnable("exec-test", "/bin/true")
        recipe_path = os.path.join(self.tmpdir.name, "recipe.json")
        runnable.write_json(recipe_path)
        self.assertTrue(os.path.exists(recipe_path))
        loaded_runnable = Runnable.from_recipe(recipe_path)
        self.assertEqual(loaded_runnable.kind, "exec-test")
        self.assertEqual(loaded_runnable.uri, "/bin/true")

    def test_runnable_to_recipe_args(self):
        runnable = Runnable("exec-test", "/bin/sleep", "0.01")
        recipe_path = os.path.join(self.tmpdir.name, "recipe.json")
        runnable.write_json(recipe_path)
        self.assertTrue(os.path.exists(recipe_path))
        loaded_runnable = Runnable.from_recipe(recipe_path)
        self.assertEqual(loaded_runnable.kind, "exec-test")
        self.assertEqual(loaded_runnable.uri, "/bin/sleep")
        self.assertEqual(loaded_runnable.args, ("0.01",))

    def tearDown(self):
        self.tmpdir.cleanup()


class Runner(unittest.TestCase):
    def test_runner_noop(self):
        runnable = Runnable("noop", None)
        runner_klass = runnable.pick_runner_class()
        runner = runner_klass()
        results = [status for status in runner.run(runnable)]
        last_result = results[-1]
        self.assertEqual(last_result["status"], "finished")
        self.assertIn("time", last_result)

    def test_runner_exec(self):
        runnable = Runnable(
            "exec-test", sys.executable, "-c", "import time; time.sleep(0.01)"
        )
        runner_klass = runnable.pick_runner_class()
        runner = runner_klass()
        results = [status for status in runner.run(runnable)]
        stdout_result = results[-3]
        stderr_result = results[-2]
        last_result = results[-1]
        self.assertEqual(stdout_result["type"], "stdout")
        self.assertEqual(stdout_result["log"], b"")
        self.assertEqual(stderr_result["type"], "stderr")
        self.assertEqual(stderr_result["log"], b"")
        self.assertEqual(last_result["status"], "finished")
        self.assertEqual(last_result["returncode"], 0)
        self.assertIn("time", last_result)

    def test_runner_exec_test_ok(self):
        runnable = Runnable(
            "exec-test", sys.executable, "-c", "import time; time.sleep(0.01)"
        )
        runner_klass = runnable.pick_runner_class()
        runner = runner_klass()
        results = [status for status in runner.run(runnable)]
        stdout_result = results[-3]
        stderr_result = results[-2]
        last_result = results[-1]
        self.assertEqual(stdout_result["type"], "stdout")
        self.assertEqual(stdout_result["log"], b"")
        self.assertEqual(stderr_result["type"], "stderr")
        self.assertEqual(stderr_result["log"], b"")
        self.assertEqual(last_result["status"], "finished")
        self.assertEqual(last_result["result"], "pass")
        self.assertEqual(last_result["returncode"], 0)
        self.assertIn("time", last_result)

    @skipUnlessPathExists("/bin/false")
    def test_runner_exec_test_fail(self):
        runnable = Runnable("exec-test", "/bin/false")
        runner_klass = runnable.pick_runner_class()
        runner = runner_klass()
        results = [status for status in runner.run(runnable)]
        stdout_result = results[-3]
        stderr_result = results[-2]
        last_result = results[-1]
        self.assertEqual(stdout_result["type"], "stdout")
        self.assertEqual(stdout_result["log"], b"")
        self.assertEqual(stderr_result["type"], "stderr")
        self.assertEqual(stderr_result["log"], b"")
        self.assertEqual(last_result["status"], "finished")
        self.assertEqual(last_result["result"], "fail")
        self.assertEqual(last_result["returncode"], 1)
        self.assertIn("time", last_result)

    def test_runner_python_unittest_ok(self):
        runnable = Runnable(
            "python-unittest", "selftests/.data/unittests.py:First.test_pass"
        )
        runner_klass = runnable.pick_runner_class()
        runner = runner_klass()
        results = [status for status in runner.run(runnable)]
        output1 = (
            b"----------------------------------------------------------------------\n"
            b"Ran 1 test in "
        )
        output2 = b"s\n\nOK\n"
        output = results[-2]
        result = results[-1]
        self.assertEqual(result["status"], "finished")
        self.assertEqual(result["result"], "pass")
        self.assertTrue(output["log"].startswith(output1), "Start of output differs")
        self.assertTrue(output["log"].endswith(output2), "End of output differs")

    def test_runner_python_unittest_fail(self):
        runnable = Runnable(
            "python-unittest", "selftests/.data/unittests.py:Second.test_fail"
        )
        runner_klass = runnable.pick_runner_class()
        runner = runner_klass()
        results = [status for status in runner.run(runnable)]
        if sys.version_info < (3, 11):
            output1 = (
                b"======================================================================\n"
                b"FAIL: test_fail (unittests.Second)\n"
            )
        else:
            output1 = (
                b"======================================================================\n"
                b"FAIL: test_fail (unittests.Second.test_fail)\n"
            )
        output2 = b"\n\nFAILED (failures=1)\n"
        output = results[-2]
        result = results[-1]
        self.assertEqual(result["status"], "finished")
        self.assertEqual(result["result"], "fail")
        self.assertTrue(output["log"].startswith(output1), "Start of output differs")
        self.assertTrue(output["log"].endswith(output2), "End of output differs")

    def test_runner_python_unittest_skip(self):
        runnable = Runnable(
            "python-unittest", "selftests/.data/unittests.py:Second.test_skip"
        )
        runner_klass = runnable.pick_runner_class()
        runner = runner_klass()
        results = [status for status in runner.run(runnable)]
        if sys.version_info < (3, 12, 1):
            output1 = (
                b"----------------------------------------------------------------------\n"
                b"Ran 1 test in "
            )
            output2 = b"s\n\nOK (skipped=1)\n"
        else:
            output1 = (
                b"----------------------------------------------------------------------\n"
                b"Ran 0 tests in "
            )
            output2 = b"\n\nNO TESTS RAN (skipped=1)\n"
        output = results[-2]
        result = results[-1]
        self.assertEqual(result["status"], "finished")
        self.assertEqual(result["result"], "skip")
        self.assertTrue(output["log"].startswith(output1), "Start of output differs")
        self.assertTrue(output["log"].endswith(output2), "End of output differs")

    def test_runner_python_unittest_error(self):
        runnable = Runnable("python-unittest", "error")
        runner_klass = runnable.pick_runner_class()
        runner = runner_klass()
        results = [status for status in runner.run(runnable)]
        output = "Invalid URI: could not be converted to an unittest dotted name."
        result = results[-1]
        self.assertEqual(result["status"], "finished")
        self.assertEqual(result["result"], "error")
        self.assertEqual(result["fail_reason"], output)

    def test_runner_python_unittest_empty_uri_error(self):
        runnable = Runnable("python-unittest", "")
        runner_klass = runnable.pick_runner_class()
        runner = runner_klass()
        results = [status for status in runner.run(runnable)]
        output = "Invalid URI: could not be converted to an unittest dotted name."
        result = results[-1]
        self.assertEqual(result["status"], "finished")
        self.assertEqual(result["result"], "error")
        self.assertEqual(result["fail_reason"], output)


class RunnerTmp(unittest.TestCase):
    def setUp(self):
        prefix = temp_dir_prefix(self)
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    @skipUnlessPathExists("/bin/sh")
    def test_runner_tap_fail(self):
        tap_script = """#!/bin/sh
echo '1..2'
echo '# Defining an basic test'
echo 'ok 1 - description 1'
echo 'not ok 2 - description 2'"""
        tap_path = os.path.join(self.tmpdir.name, "tap.sh")

        with open(tap_path, "w", encoding="utf-8") as fp:
            fp.write(tap_script)

        runnable = Runnable("tap", "/bin/sh", tap_path)
        runner = runner_tap.TAPRunner()
        results = [status for status in runner.run(runnable)]
        last_result = results[-1]
        self.assertEqual(last_result["status"], "finished")
        self.assertEqual(last_result["result"], "fail")
        self.assertEqual(last_result["returncode"], 0)

    @skipUnlessPathExists("/bin/sh")
    def test_runner_tap_ok(self):
        tap_script = """#!/bin/sh
echo '1..2'
echo '# Defining an basic test'
echo 'ok 1 - description 1'
echo 'ok 2 - description 2'"""
        tap_path = os.path.join(self.tmpdir.name, "tap.sh")

        with open(tap_path, "w", encoding="utf-8") as fp:
            fp.write(tap_script)

        runnable = Runnable("tap", "/bin/sh", tap_path)
        runner = runner_tap.TAPRunner()
        results = [status for status in runner.run(runnable)]
        last_result = results[-1]
        self.assertEqual(last_result["status"], "finished")
        self.assertEqual(last_result["result"], "pass")
        self.assertEqual(last_result["returncode"], 0)

    @skipUnlessPathExists("/bin/sh")
    def test_runner_tap_skip(self):
        tap_script = """#!/bin/sh
echo '1..2'
echo '# Defining an basic test'
echo 'ok 1 - # SKIP description 1'
echo 'ok 2 - description 2'"""
        tap_path = os.path.join(self.tmpdir.name, "tap.sh")

        with open(tap_path, "w", encoding="utf-8") as fp:
            fp.write(tap_script)

        runnable = Runnable("tap", "/bin/sh", tap_path)
        runner = runner_tap.TAPRunner()
        results = [status for status in runner.run(runnable)]
        last_result = results[-1]
        self.assertEqual(last_result["status"], "finished")
        self.assertEqual(last_result["result"], "skip")
        self.assertEqual(last_result["returncode"], 0)

    @skipUnlessPathExists("/bin/sh")
    def test_runner_tap_bailout(self):
        tap_script = """#!/bin/sh
echo '1..2'
echo '# Defining an basic test'
echo 'Bail out! - description 1'
echo 'ok 2 - description 2'"""
        tap_path = os.path.join(self.tmpdir.name, "tap.sh")

        with open(tap_path, "w", encoding="utf-8") as fp:
            fp.write(tap_script)

        runnable = Runnable("tap", "/bin/sh", tap_path)
        runner = runner_tap.TAPRunner()
        results = [status for status in runner.run(runnable)]
        last_result = results[-1]
        self.assertEqual(last_result["status"], "finished")
        self.assertEqual(last_result["result"], "error")
        self.assertEqual(last_result["returncode"], 0)

    @skipUnlessPathExists("/bin/sh")
    def test_runner_tap_error(self):
        tap_script = """#!/bin/sh
echo '1..2'
echo '# Defining an basic test'
echo 'error - description 1'
echo 'ok 2 - description 2'"""
        tap_path = os.path.join(self.tmpdir.name, "tap.sh")

        with open(tap_path, "w", encoding="utf-8") as fp:
            fp.write(tap_script)

        runnable = Runnable("tap", "/bin/sh", tap_path)
        runner = runner_tap.TAPRunner()
        results = [status for status in runner.run(runnable)]
        last_result = results[-1]
        self.assertEqual(last_result["status"], "finished")
        self.assertEqual(last_result["result"], "error")
        self.assertEqual(last_result["returncode"], 0)

    def tearDown(self):
        self.tmpdir.cleanup()


@skipUnlessPathExists("/bin/sh")
class RunnerCommandSelection(unittest.TestCase):
    def setUp(self):
        self.kind = "mykind"

    @unittest.skipIf(
        sys.platform.startswith("darwin"),
        "echo implementation under darwin lacks the -n feature",
    )
    def test_is_task_kind_supported(self):
        cmd = [
            "sh",
            "-c",
            'test $0 = capabilities && echo -n {\\"runnables\\": [\\"mykind\\"]}',
        ]
        self.assertTrue(Runnable.is_kind_supported_by_runner_command(self.kind, cmd))

    def test_is_task_kind_supported_other_kind(self):
        cmd = [
            "sh",
            "-c",
            'test $0 = capabilities && echo -n {\\"runnables\\": [\\"otherkind\\"]}',
        ]
        self.assertFalse(Runnable.is_kind_supported_by_runner_command(self.kind, cmd))

    def test_is_task_kind_supported_no_output(self):
        cmd = ["sh", "-c", 'echo -n ""']
        self.assertFalse(Runnable.is_kind_supported_by_runner_command(self.kind, cmd))


class PickRunner(unittest.TestCase):
    def setUp(self):
        self.kind = "lets-image-a-kind"

    def test_pick_runner_command(self):
        runner = ["avocado-runner-lets-image-a-kind"]
        known = {"lets-image-a-kind": runner}
        self.assertEqual(Runnable.pick_runner_command(self.kind, known), runner)

    def test_pick_runner_command_empty(self):
        self.assertFalse(Runnable.pick_runner_command(self.kind, {}))


class TaskTest(unittest.TestCase):
    def test_default_category(self):
        runnable = Runnable("noop", "noop_uri")
        task = Task(runnable, "task_id")
        self.assertEqual(task.category, "test")

    def test_set_category(self):
        runnable = Runnable("noop", "noop_uri")
        task = Task(runnable, "task_id", category="new_category")
        self.assertEqual(task.category, "new_category")


if __name__ == "__main__":
    unittest.main()
