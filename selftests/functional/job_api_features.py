"""
Functional tests for features available through the job API
"""

import os
import unittest

from avocado.core import exit_codes
from avocado.core.job import Job
from avocado.core.nrunner.runnable import Runnable
from avocado.core.suite import TestSuite
from selftests.utils import TestCaseTmpDir


class Test(TestCaseTmpDir):
    def setUp(self):
        super().setUp()
        self.base_config = {
            "core.show": ["none"],
            "run.results_dir": self.tmpdir.name,
            "resolver.references": ["examples/tests/passtest.py"],
        }

    def test_job_run_result_json_enabled(self):
        self.base_config["job.run.result.json.enabled"] = True
        with Job.from_config(self.base_config) as j:
            result = j.run()
        self.assertEqual(result, exit_codes.AVOCADO_ALL_OK)
        json_results_path = os.path.join(self.tmpdir.name, "latest", "results.json")
        self.assertTrue(os.path.exists(json_results_path))

    def test_job_run_result_json_output(self):
        json_results_path = os.path.join(self.tmpdir.name, "myresults.json")
        self.base_config["job.run.result.json.output"] = json_results_path
        with Job.from_config(self.base_config) as j:
            result = j.run()
        self.assertEqual(result, exit_codes.AVOCADO_ALL_OK)
        self.assertTrue(os.path.exists(json_results_path))

    def test_job_params(self):
        test = Runnable(
            "avocado-instrumented",
            "examples/tests/sleeptest.py:SleepTest.test",
            variant={
                "paths": ["/"],
                "variant_id": None,
                "variant": [["/", [["/", "sleep_length", "0.01"]]]],
            },
        )
        suite = TestSuite("suite_1", tests=[test], config=self.base_config)
        with Job(self.base_config, [suite]) as j:
            result = j.run()
            test_runtime = j.result.tests[0].get("time_elapsed")
        self.assertEqual(result, exit_codes.AVOCADO_ALL_OK)
        self.assertLess(
            test_runtime, 1, "SleepTest runtime was longer than parameter enforced."
        )

    def test_runnable_output_dir(self):
        """It checks if Runnable is able to set its own output_dir."""

        test_dir = os.path.join(self.tmpdir.name, "latest", "test-results")
        output_dir = os.path.join(test_dir, "test")
        tests = [
            Runnable(
                "avocado-instrumented",
                "examples/tests/passtest.py:PassTest.test",
                output_dir=output_dir,
            ),
            Runnable(
                "avocado-instrumented",
                "examples/tests/failtest.py:FailTest.test",
                output_dir=output_dir,
            ),
        ]

        suite = TestSuite("suite_1", tests=tests, config=self.base_config)
        with Job(self.base_config, [suite]) as j:
            j.run()
        self.assertTrue(os.path.exists(os.path.join(test_dir, "test")))
        self.assertEqual(len(os.listdir(test_dir)), 2)
        test_logfile = os.path.join(output_dir, "debug.log")
        with open(test_logfile, "r", encoding="utf-8") as debug_file:
            logs = debug_file.read()
            self.assertIn("INIT 1-examples/tests/failtest.py:FailTest.test", logs)
            self.assertIn("INIT 1-examples/tests/passtest.py:PassTest.test", logs)


if __name__ == "__main__":
    unittest.main()
