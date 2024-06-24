import sys
import unittest

from avocado.core.nrunner.runnable import Runnable
from selftests.utils import skipUnlessPathExists


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
        if sys.version_info == (3, 12, 1):
            output1 = (
                b"----------------------------------------------------------------------\n"
                b"Ran 0 tests in "
            )
            output2 = b"\n\nNO TESTS RAN (skipped=1)\n"
        else:
            output1 = (
                b"----------------------------------------------------------------------\n"
                b"Ran 1 test in "
            )
            output2 = b"s\n\nOK (skipped=1)\n"
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
