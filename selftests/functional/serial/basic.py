import os
import re
import signal
import time

from avocado.utils import process, script
from selftests.utils import AVOCADO, TestCaseTmpDir

SLEEP_TEST = """import time

from avocado import Test


class SleepTest(Test):

    timeout = 10

    def test(self):
        self.log.debug("Sleeping starts: %s", time.time())
        time.sleep(9)
        self.log.debug("Sleeping ends: %s", time.time())
"""


class RunnerOperationTest(TestCaseTmpDir):
    def test_pause(self):
        with script.TemporaryScript(
            "sleep.py",
            SLEEP_TEST,
        ) as tst:
            cmd_line = f"{AVOCADO} run --disable-sysinfo --job-results-dir {self.tmpdir.name} -- {tst}"
            proc = process.SubProcess(cmd_line)
            proc.start()
            init = True
            while init:
                output = proc.get_stdout()
                if b"STARTED" in output:
                    init = False
            proc.send_signal(signal.SIGTSTP)
            time.sleep(10)
            proc.send_signal(signal.SIGTSTP)
            proc.wait()
            full_log_path = os.path.join(self.tmpdir.name, "latest", "full.log")
            with open(full_log_path, encoding="utf-8") as full_log_file:
                full_log = full_log_file.read()
            regex_start = re.search("Sleeping starts: ([0-9]*)", full_log)
            regex_end = re.search("Sleeping ends: ([0-9]*)", full_log)
            start_time = int(regex_start.group(1))
            start_end = int(regex_end.group(1))
            self.assertIn("SleepTest.test: PAUSED", full_log)
            self.assertIn("SleepTest.test: STARTED", full_log)
            self.assertGreaterEqual(start_end - start_time, 7)
