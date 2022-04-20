import os
import sys
import unittest

from avocado.utils import process
from selftests.utils import BASEDIR

RUNNER = f"{sys.executable} -m avocado.plugins.runners.package"


class RunnableRun(unittest.TestCase):

    def test_no_kwargs(self):
        res = process.run(f"{RUNNER} runnable-run -k package",
                          ignore_status=True)
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'time': ", res.stdout)
        self.assertEqual(res.exit_status, 0)

    def test_action_check_alone(self):
        action = 'action=check'
        res = process.run(f"{RUNNER} runnable-run -k package {action}",
                          ignore_status=True)
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'time': ", res.stdout)
        self.assertIn(b"'log': b\'Package name should be passed as kwargs",
                      res.stdout)
        self.assertEqual(res.exit_status, 0)

    @unittest.skipUnless(os.getenv('CI'), "This test runs on CI environments"
                         " only as it depends on the system package manager,"
                         " and some environments don't have it available.")
    def test_recipe(self):
        recipe = os.path.join(BASEDIR, "examples", "nrunner",
                              "recipes", "runnables",
                              "package_check_foo.json")
        cmd = f"{RUNNER} runnable-run-recipe {recipe}"
        res = process.run(cmd, ignore_status=True)
        lines = res.stdout_text.splitlines()
        if len(lines) == 1:
            first_status = final_status = lines[0]
        else:
            first_status = lines[0]
            final_status = lines[-1]
        self.assertIn("'status': 'started'", first_status)
        self.assertIn("'time': ", first_status)
        self.assertIn("'status': 'finished'", final_status)
        self.assertIn("'time': ", final_status)
        self.assertIn(b"'log': b'Package foo not installed'", res.stdout)
        self.assertEqual(res.exit_status, 0)


class TaskRun(unittest.TestCase):

    def test_no_kwargs(self):
        res = process.run(f"{RUNNER} task-run -i XXXreq-pacXXX -k package",
                          ignore_status=True)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'result': 'error'", res.stdout)
        self.assertIn(b"'id': 'XXXreq-pacXXX'", res.stdout)
        self.assertEqual(res.exit_status, 0)


if __name__ == '__main__':
    unittest.main()
