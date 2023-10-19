import json
import os
import unittest

from avocado.core.job import Job
from avocado.utils import process, script
from selftests.utils import AVOCADO, TestCaseTmpDir, python_module_available

TEST_LOGDIR = """from avocado import Test


class LogdirTest(Test):

    def test(self):
        self.log.debug("logdir is: %s" % self.logdir)
"""


class ProcessSpawnerTest(TestCaseTmpDir):
    def test_logdir_path(self):
        test = script.Script(
            os.path.join(self.tmpdir.name, "logdir_test.py"), TEST_LOGDIR
        )
        test.save()
        result = process.run(
            f"{AVOCADO} run "
            f"--job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo --json - -- {test}"
        )
        res = json.loads(result.stdout_text)
        logfile = res["tests"][0]["logfile"]
        testdir = res["tests"][0]["logdir"]
        with open(logfile, "r", encoding="utf-8") as debug_file:
            expected = f"logdir is: {testdir}"
            self.assertIn(expected, debug_file.read())

    @unittest.skipUnless(
        python_module_available("avocado-rogue"), "avocado-rogue not available"
    )
    def test_rogue_runner(self):
        config = {
            "resolver.references": ["x-avocado-runner-rogue"],
            "run.results_dir": self.tmpdir.name,
            "task.timeout.running": 2,
            "run.spawner": "process",
            "sysinfo.collect.enabled": False,
        }

        with Job.from_config(job_config=config) as job:
            job.run()

        self.assertEqual(1, job.result.interrupted)
        self.assertEqual(0, job.result.passed)
        self.assertEqual(0, job.result.skipped)
        self.assertEqual(
            "Test interrupted: Timeout reached", job.result.tests[0]["fail_reason"]
        )

        logfile = os.path.join(self.tmpdir.name, "latest", "full.log")
        with open(logfile, "r", encoding="utf-8") as full_log:
            self.assertIn(
                'Could not terminate task "1-1-x-avocado-runner-rogue"', full_log.read()
            )
