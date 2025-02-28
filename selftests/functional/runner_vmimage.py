import os
import sys
import unittest

from avocado.core.nrunner.runnable import Runnable
from avocado.plugins.runners.vmimage import VMImageRunner
from avocado.utils import path, process
from selftests.utils import AVOCADO, BASEDIR, TestCaseTmpDir

RUNNER = f"{sys.executable} -m avocado.plugins.runners.vmimage"


class RunnableRunVMImage(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("AVOCADO_SELFTESTS_NETWORK_ENABLED", False),
        "Network required to run these tests",
    )
    def test_no_kwargs(self):
        res = process.run(f"{RUNNER} runnable-run -k vmimage", ignore_status=True)
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'time': ", res.stdout)
        self.assertEqual(res.exit_status, 0)


class TaskRunVMImage(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("AVOCADO_SELFTESTS_NETWORK_ENABLED", False),
        "Network required to run these tests",
    )
    def test_no_kwargs(self):
        res = process.run(
            f"{RUNNER} task-run -i vmimage_1 -k vmimage", ignore_status=True
        )
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'result': 'error'", res.stdout)
        self.assertIn(b"'id': 'vmimage_1'", res.stdout)
        self.assertEqual(res.exit_status, 0)


class VMImageTest(TestCaseTmpDir):
    @unittest.skipUnless(
        os.environ.get("AVOCADO_SELFTESTS_NETWORK_ENABLED", False),
        "Network required to run these tests",
    )
    def test_vmimage_dependencies(self):
        test_path = os.path.join(
            BASEDIR,
            "examples",
            "tests",
            "dependency_vmimage.py",
        )
        cmd = f"{AVOCADO} run --job-results-dir '{self.tmpdir.name}' '{test_path}'"

        res = process.run(cmd, ignore_status=True, shell=True)

        self.assertEqual(
            res.exit_status,
            0,
            f"Command failed with exit {res.exit_status}. Stderr: {res.stderr}",
        )

        self.assertIn(
            b"RESULTS    : PASS 5 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0",
            res.stdout,
            f"Unexpected test results. Full stdout: {res.stdout}",
        )

    @unittest.skipUnless(
        os.environ.get("AVOCADO_SELFTESTS_NETWORK_ENABLED", False),
        "Network required to run these tests",
    )
    def test_vmimage_runner(self):
        res = process.run(
            f"{RUNNER} task-run -i vmimage_0 -k vmimage "
            "provider=Fedora version=41 arch=x86_64",
            ignore_status=True,
            shell=True,
        )
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'result': 'pass'", res.stdout)
        self.assertEqual(res.exit_status, 0)

    @unittest.skipUnless(
        os.environ.get("AVOCADO_SELFTESTS_NETWORK_ENABLED", False),
        "Network required to run these tests",
    )
    def test_vmimage_task(self):
        res = process.run(
            f"{RUNNER} task-run -i vmimage_2 -k vmimage "
            "provider=Fedora version=41 arch=x86_64",
            ignore_status=True,
            shell=True,
        )
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'result': 'pass'", res.stdout)
        self.assertIn(b"'id': 'vmimage_2'", res.stdout)
        self.assertEqual(res.exit_status, 0)

    @unittest.skipUnless(
        os.environ.get("AVOCADO_SELFTESTS_NETWORK_ENABLED", False),
        "Network required to run these tests",
    )
    def test_vmimage_basic(self):
        runnable = Runnable(
            "vmimage",
            "",
            kwargs={
                "provider": "Fedora",
                "version": "41",
                "arch": "x86_64",
            },
        )
        runner = VMImageRunner()
        try:
            results = [status for status in runner.run(runnable)]
        except Exception as e:
            self.fail(f"Runner raised an exception: {str(e)}")

        self.assertEqual(results[0]["status"], "started")
        self.assertEqual(results[-1]["status"], "finished")
        self.assertEqual(results[-1].get("result"), "pass")

    @unittest.skipUnless(
        os.environ.get("AVOCADO_SELFTESTS_NETWORK_ENABLED", False),
        "Network required to run these tests",
    )
    def test_missing_params(self):
        runnable = Runnable(
            "vmimage",
            "",
            kwargs={
                "provider": "Fedora",
            },
        )
        runner = VMImageRunner()
        results = [status for status in runner.run(runnable)]

        self.assertEqual(results[-1]["status"], "finished")
        self.assertEqual(results[-1]["result"], "error")

    def tearDown(self):
        self.tmpdir.cleanup()
        super().tearDown()


if __name__ == "__main__":
    unittest.main()
