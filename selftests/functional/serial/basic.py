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


@unittest.skipIf(
    sys.platform.startswith("darwin"),
    "The test pause feature is not supported on macOS",
)
class RunnerOperationTest(TestCaseTmpDir):
    def _count_lines(self, file_path):
        with open(os.path.join(file_path, "sleep.txt"), encoding="utf-8") as file:
            return sum(1 for _ in file)

    def _check_pause(self, tst):
        cmd_line = f"{AVOCADO} run --disable-sysinfo --job-results-dir {self.tmpdir.name} -- {tst}"
        proc = process.SubProcess(cmd_line)
        proc.start()
        init = True
        while init:
            output = proc.get_stdout()
            if b"STARTED" in output:
                init = False
        time.sleep(2)
        proc.send_signal(signal.SIGTSTP)
        time.sleep(1)
        test_log_dir = glob.glob(
            os.path.join(self.tmpdir.name, "job-*", "test-results", "*")
        )[0]
        lines = self._count_lines(test_log_dir)
        self.assertNotEqual(
            lines,
            10,
            "The test finished before it was paused",
        )
        time.sleep(5)
        self.assertEqual(
            lines,
            self._count_lines(test_log_dir),
            "The test was not paused",
        )
        proc.send_signal(signal.SIGTSTP)
        proc.wait()
        full_log_path = os.path.join(self.tmpdir.name, "latest", "full.log")
        with open(full_log_path, encoding="utf-8") as full_log_file:
            full_log = full_log_file.read()
        self.assertIn("PAUSED", full_log)
        self.assertIn("STARTED", full_log)
        self.assertEqual(
            self._count_lines(test_log_dir),
            10,
            "The test was not resumed",
        )

    def test_pause_exec(self):
        with script.TemporaryScript(
            "sleep.sh",
            SLEEP_TEST_EXEC,
        ) as tst_exec:
            self._check_pause(tst_exec)

    def test_pause_instrumented(self):

        with script.TemporaryScript(
            "sleep.py",
            SLEEP_TEST_PYTHON,
        ) as tst_python:
            self._check_pause(tst_python)
