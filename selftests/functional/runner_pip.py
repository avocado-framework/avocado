import os
import sys
import unittest

from avocado.utils import process
from selftests.utils import AVOCADO, BASEDIR, TestCaseTmpDir

RUNNER = f"{sys.executable} -m avocado.plugins.runners.pip"


class RunnableRun(unittest.TestCase):
    def test_no_kwargs(self):
        res = process.run(f"{RUNNER} runnable-run -k pip", ignore_status=True)
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'time': ", res.stdout)
        self.assertEqual(res.exit_status, 0)


class TaskRun(unittest.TestCase):
    def test_no_kwargs(self):
        res = process.run(f"{RUNNER} task-run -i pip_1 -k pip", ignore_status=True)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'result': 'error'", res.stdout)
        self.assertIn(b"'id': 'pip_1'", res.stdout)
        self.assertEqual(res.exit_status, 0)


class PipTest(TestCaseTmpDir):
    def test_pip_dependencies(self):
        test_path = os.path.join(
            BASEDIR,
            "examples",
            "tests",
            "dependency_pip.py",
        )
        res = process.run(
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} {test_path}",
            ignore_status=True,
        )
        self.assertIn(
            b"RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0",
            res.stdout,
        )
        self.assertEqual(res.exit_status, 0)


if __name__ == "__main__":
    unittest.main()
