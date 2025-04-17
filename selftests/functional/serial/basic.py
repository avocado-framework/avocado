import glob
import os
import signal
import sys
import time
import unittest

from avocado.utils import process, script
from selftests.utils import AVOCADO, TestCaseTmpDir

SLEEP_TEST_PYTHON = """import os
import time

from avocado import Test


class SleepTest(Test):

    def test(self):
        with open(os.path.join(self.logdir, "sleep.txt"), "w") as f:
            for _ in range(10):
                f.write("Sleeping \\n")
                time.sleep(1)
"""

SLEEP_TEST_EXEC = """#!/bin/bash
output_file="$AVOCADO_TEST_LOGDIR/sleep.txt"
for i in {1..10}; do
    echo "This is line $i" >> "$output_file"
    sleep 1
done
"""


class RunnerOperationTest(TestCaseTmpDir):
    @unittest.skipIf(
        sys.platform.startswith("darwin"),
        "The test pause feature is not supported on macOS",
    )
    def test_pause(self):
        def count_lines(file_path):
            with open(os.path.join(file_path, "sleep.txt"), encoding="utf-8") as file:
                return sum(1 for _ in file)

        with script.TemporaryScript(
            "sleep.py",
            SLEEP_TEST_PYTHON,
        ) as tst_python:
            with script.TemporaryScript(
                "sleep.sh",
                SLEEP_TEST_EXEC,
            ) as tst_exec:
                cmd_line = f"{AVOCADO} run --disable-sysinfo --job-results-dir {self.tmpdir.name} -- {tst_python} {tst_exec}"
                proc = process.SubProcess(cmd_line)
                proc.start()
                init = True
                while init:
                    output = proc.get_stdout()
                    if b"STARTED" in output:
                        init = False
                time.sleep(1)
                proc.send_signal(signal.SIGTSTP)
                python_test_log_dir = glob.glob(
                    os.path.join(self.tmpdir.name, "job-*", "test-results", "*.py*")
                )[0]
                python_lines = count_lines(python_test_log_dir)
                exec_test_log_dir = glob.glob(
                    os.path.join(self.tmpdir.name, "job-*", "test-results", "*.sh")
                )[0]
                time.sleep(1)
                exec_lines = count_lines(exec_test_log_dir)
                time.sleep(5)
                self.assertEqual(
                    python_lines,
                    count_lines(python_test_log_dir),
                    "The python test was not paused",
                )
                self.assertEqual(
                    exec_lines,
                    count_lines(exec_test_log_dir),
                    "The exec test was not paused",
                )
                proc.send_signal(signal.SIGTSTP)
                proc.wait()
                full_log_path = os.path.join(self.tmpdir.name, "latest", "full.log")
                with open(full_log_path, encoding="utf-8") as full_log_file:
                    full_log = full_log_file.read()
                self.assertIn("SleepTest.test: PAUSED", full_log)
                self.assertIn("SleepTest.test: STARTED", full_log)
                self.assertEqual(
                    count_lines(python_test_log_dir),
                    10,
                    "The python tests was not resumed",
                )
                self.assertEqual(
                    count_lines(exec_test_log_dir), 10, "The exec tests was not resumed"
                )
