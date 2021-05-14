import os
import sys
import unittest

from avocado.utils import process
from selftests.utils import BASEDIR

RUNNER = "%s -m avocado.core.runners.requirement_asset" % sys.executable


class RunnableRun(unittest.TestCase):

    skip_message = ('This test depends on internet connectivity.'
                    'Skipping to run on CI only.')

    def test_no_kwargs(self):
        res = process.run("%s runnable-run -k requirement-asset" % RUNNER,
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
        res = process.run("%s runnable-run -k requirement-asset %s %s"
                          % (RUNNER, name, locations), ignore_status=True)
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
                              "requirement_asset.json")
        cmd = "%s runnable-run-recipe %s" % (RUNNER, recipe)
        res = process.run(cmd, ignore_status=True)
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'log': b\'File fetched at", res.stdout)
        self.assertEqual(res.exit_status, 0)


class TaskRun(unittest.TestCase):

    def test_no_kwargs(self):
        res = process.run("%s task-run -i XXXreq-pacXXX -k requirement-asset"
                          % RUNNER, ignore_status=True)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'result': 'error'", res.stdout)
        self.assertIn(b"'id': 'XXXreq-pacXXX'", res.stdout)
        self.assertEqual(res.exit_status, 0)


if __name__ == '__main__':
    unittest.main()
