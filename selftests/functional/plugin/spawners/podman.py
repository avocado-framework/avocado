import glob
import os

from avocado import Test
from avocado.core.job import Job
from avocado.utils import process, script
from selftests.utils import AVOCADO, BASEDIR

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


class PodmanSpawnerTest(Test):
    """
    :avocado: dependency={"type": "package", "name": "podman", "action": "check"}
    :avocado: dependency={"type": "podman-image", "uri": "registry.fedoraproject.org/fedora:38"}
    """

    def test_avocado_instrumented(self):

        with script.Script(
            os.path.join(self.workdir, "passtest.py"), TEST_INSTRUMENTED_PASS
        ) as test:
            result = process.run(
                f"{AVOCADO} run "
                f"--job-results-dir {self.workdir} "
                f"--disable-sysinfo --spawner=podman "
                f"--spawner-podman-image=fedora:38 -- "
                f"{test}",
                ignore_status=True,
            )
        self.assertEqual(result.exit_status, 0)
        self.assertIn("passtest.py:PassTest.test: STARTED", result.stdout_text)
        self.assertIn("passtest.py:PassTest.test:  PASS", result.stdout_text)

    def test_exec(self):
        result = process.run(
            f"{AVOCADO} run "
            f"--job-results-dir {self.workdir} "
            f"--disable-sysinfo --spawner=podman "
            f"--spawner-podman-image=fedora:38 -- "
            f"/bin/true",
            ignore_status=True,
        )
        self.assertEqual(result.exit_status, 0)
        self.assertIn("/bin/true: STARTED", result.stdout_text)
        self.assertIn("/bin/true:  PASS", result.stdout_text)

    def test_sleep_longer_timeout_podman(self):

        with script.Script(
            os.path.join(self.workdir, "sleeptest.py"), TEST_INSTRUMENTED_SLEEP
        ) as test:
            config = {
                "resolver.references": [test.path],
                "run.results_dir": self.workdir,
                "task.timeout.running": 2,
                "run.spawner": "podman",
                "spawner.podman.image": "fedora:38",
            }

            with Job.from_config(job_config=config) as job:
                job.run()

        self.assertEqual(1, job.result.interrupted)
        self.assertEqual(0, job.result.passed)
        self.assertEqual(0, job.result.skipped)
        self.assertEqual(
            "Test interrupted: Timeout reached", job.result.tests[0]["fail_reason"]
        )

    def test_outputdir(self):
        config = {
            "resolver.references": [
                os.path.join(BASEDIR, "examples", "tests", "gendata.py")
            ],
            "run.results_dir": self.workdir,
            "run.spawner": "podman",
            "spawner.podman.image": "fedora:38",
        }

        with Job.from_config(job_config=config) as job:
            job.run()

        self.assertEqual(1, job.result.passed)
        data_files = glob.glob(os.path.join(job.test_results_path, "1-*", "data", "*"))
        self.assertEqual(len(data_files), 1)
        self.assertTrue(data_files[0].endswith("test.json"))

    def test_asset_files(self):
        test = os.path.join(BASEDIR, "examples", "tests", "use_data.sh")
        result = process.run(
            f"{AVOCADO} run "
            f"--job-results-dir {self.workdir} "
            f"--disable-sysinfo --spawner=podman "
            f"--spawner-podman-image=fedora:38 -- "
            f"{test}",
            ignore_status=True,
        )
        self.assertEqual(result.exit_status, 0)
        self.assertIn("use_data.sh: STARTED", result.stdout_text)
        self.assertIn("use_data.sh:  PASS", result.stdout_text)
