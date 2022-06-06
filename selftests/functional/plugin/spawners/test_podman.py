import os
import shutil
import unittest

from avocado.utils import process, script
from selftests.utils import AVOCADO, TestCaseTmpDir

TEST_INSTRUMENTED_PASS = """from avocado import Test


class PassTest(Test):

    def test(self):
        pass
"""


@unittest.skipIf(shutil.which('podman') is None,
                 "Podman not installed (command podman is missing)")
class PodmanSpawnerTest(TestCaseTmpDir):

    def test_avocado_instrumented(self):

        with script.Script(os.path.join(self.tmpdir.name, "passtest.py"),
                           TEST_INSTRUMENTED_PASS) as test:
            result = process.run(f"{AVOCADO} run "
                                 f"--job-results-dir {self.tmpdir.name} "
                                 f"--disable-sysinfo --nrunner-spawner=podman "
                                 f"--spawner-podman-image=fedora:latest -- "
                                 f"{test}", ignore_status=True)
        self.assertEqual(result.exit_status, 0)
        self.assertIn("passtest.py:PassTest.test: STARTED", result.stdout_text)
        self.assertIn("passtest.py:PassTest.test:  PASS", result.stdout_text)

    def test_exec(self):
        result = process.run(f"{AVOCADO} run "
                             f"--job-results-dir {self.tmpdir.name} "
                             f"--disable-sysinfo --nrunner-spawner=podman "
                             f"--spawner-podman-image=fedora:latest -- "
                             f"/bin/true", ignore_status=True)
        self.assertEqual(result.exit_status, 0)
        self.assertIn("/bin/true: STARTED", result.stdout_text)
        self.assertIn("/bin/true:  PASS", result.stdout_text)
