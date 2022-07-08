import os
import shutil
import unittest

from avocado.core.job import Job
from avocado.utils import process, script
from selftests.utils import AVOCADO, TestCaseTmpDir

TEST_INSTRUMENTED_PASS = """from avocado import Test


class PassTest(Test):

    def test(self):
        pass
"""

TEST_INSTRUMENTED_SLEEP = """import time
from avocado import Test


class PassTest(Test):

    def test(self):
        time.sleep(10)
"""


@unittest.skipIf(
    shutil.which("podman") is None, "Podman not installed (command podman is missing)"
)
class PodmanSpawnerTest(TestCaseTmpDir):
    def test_avocado_instrumented(self):

        with script.Script(
            os.path.join(self.tmpdir.name, "passtest.py"), TEST_INSTRUMENTED_PASS
        ) as test:
            result = process.run(
                f"{AVOCADO} run "
                f"--job-results-dir {self.tmpdir.name} "
                f"--disable-sysinfo --nrunner-spawner=podman "
                f"--spawner-podman-image=fedora:latest -- "
                f"{test}",
                ignore_status=True,
            )
        self.assertEqual(result.exit_status, 0)
        self.assertIn("passtest.py:PassTest.test: STARTED", result.stdout_text)
        self.assertIn("passtest.py:PassTest.test:  PASS", result.stdout_text)

    def test_exec(self):
        result = process.run(
            f"{AVOCADO} run "
            f"--job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo --nrunner-spawner=podman "
            f"--spawner-podman-image=fedora:latest -- "
            f"/bin/true",
            ignore_status=True,
        )
        self.assertEqual(result.exit_status, 0)
        self.assertIn("/bin/true: STARTED", result.stdout_text)
        self.assertIn("/bin/true:  PASS", result.stdout_text)

    def test_sleep_longer_timeout_podman(self):

        with script.Script(
            os.path.join(self.tmpdir.name, "sleeptest.py"), TEST_INSTRUMENTED_SLEEP
        ) as test:
            config = {
                "resolver.references": [test.path],
                "run.results_dir": self.tmpdir.name,
                "task.timeout.running": 2,
                "nrunner.spawner": "podman",
                "spawner.podman.image": "fedora:latest",
            }

            with Job.from_config(job_config=config) as job:
                job.run()

        self.assertEqual(1, job.result.interrupted)
        self.assertEqual(0, job.result.passed)
        self.assertEqual(0, job.result.skipped)
        self.assertEqual(
            "Test interrupted: Timeout reached", job.result.tests[0]["fail_reason"]
        )
