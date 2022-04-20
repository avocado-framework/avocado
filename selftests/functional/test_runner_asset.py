import os
import sys
import unittest

from avocado.utils import process
from selftests.utils import BASEDIR

RUNNER = f"{sys.executable} -m avocado.plugins.runners.asset"


class RunnableRun(unittest.TestCase):

    skip_message = ('This test depends on internet connectivity.'
                    'Skipping to run on CI only.')

    def test_no_kwargs(self):
        res = process.run(f"{RUNNER} runnable-run -k asset",
                          ignore_status=True)
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"At least name should be passed as kwargs", res.stdout)
        self.assertIn(b"'time': ", res.stdout)
        self.assertEqual(res.exit_status, 0)

    @unittest.skipUnless(os.getenv('CI'), skip_message)
    def test_fetch(self):
        name = 'name=gpl-2.0.txt'
        locations = 'locations=https://mirrors.kernel.org/gnu/Licenses/gpl-2.0.txt'
        res = process.run(f"{RUNNER} runnable-run -k asset {name} {locations}",
                          ignore_status=True)
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'time': ", res.stdout)
        self.assertIn(b"'log': b\'File fetched at",
                      res.stdout)
        self.assertEqual(res.exit_status, 0)

    @unittest.skipUnless(os.getenv('CI'), skip_message)
    def test_recipe(self):
        recipe = os.path.join(BASEDIR, "examples", "nrunner",
                              "recipes", "runnables",
                              "asset.json")
        cmd = f"{RUNNER} runnable-run-recipe {recipe}"
        res = process.run(cmd, ignore_status=True)
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'log': b\'File fetched at", res.stdout)
        self.assertEqual(res.exit_status, 0)


class TaskRun(unittest.TestCase):

    def test_no_kwargs(self):
        res = process.run(f"{RUNNER} task-run -i XXXreq-pacXXX -k asset",
                          ignore_status=True)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'result': 'error'", res.stdout)
        self.assertIn(b"'id': 'XXXreq-pacXXX'", res.stdout)
        self.assertEqual(res.exit_status, 0)


if __name__ == '__main__':
    unittest.main()
