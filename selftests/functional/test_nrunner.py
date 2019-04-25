import unittest
import os

from .. import AVOCADO, BASEDIR

from avocado.utils import process
from avocado.core import exit_codes


class RunnableRun(unittest.TestCase):

    def test_noop(self):
        res = process.run("%s runnable-run -k noop" % AVOCADO,
                          ignore_status=True)
        self.assertEqual(res.stdout, b"{'status': 'finished'}\n")
        self.assertEqual(res.exit_status, exit_codes.AVOCADO_ALL_OK)


class TaskRun(unittest.TestCase):

    def test_noop(self):
        res = process.run("%s task-run -i XXXno-opXXX -k noop" % AVOCADO,
                          ignore_status=True)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'id': 'XXXno-opXXX'", res.stdout)
        self.assertEqual(res.exit_status, exit_codes.AVOCADO_ALL_OK)

    @unittest.skipUnless(os.path.exists('/bin/uname'),
                         ('Executable "/bin/uname" used in recipe is not '
                          'available in the system'))
    def test_recipe_exec_1(self):
        recipe = os.path.join(BASEDIR, "examples", "recipes", "tasks", "exec",
                              "1-uname.json")
        cmd = "%s task-run-recipe %s" % (AVOCADO, recipe)
        res = process.run(cmd, ignore_status=True)
        lines = res.stdout_text.splitlines()
        if len(lines) == 1:
            first_status = final_status = lines[0]
        else:
            first_status = lines[0]
            final_status = lines[-1]
            self.assertIn("'status': 'running'", first_status)
            self.assertIn("'id': 1", first_status)
        self.assertIn("'id': 1", first_status)
        self.assertIn("'status': 'finished'", final_status)
        self.assertEqual(res.exit_status, exit_codes.AVOCADO_ALL_OK)

    @unittest.skipUnless(os.path.exists('/bin/echo'),
                         ('Executable "/bin/echo" used in recipe is not '
                          'available in the system'))
    def test_recipe_exec_2(self):
        recipe = os.path.join(BASEDIR, "examples", "recipes", "tasks", "exec",
                              "2-echo.json")
        cmd = "%s task-run-recipe %s" % (AVOCADO, recipe)
        res = process.run(cmd, ignore_status=True)
        lines = res.stdout_text.splitlines()
        if len(lines) == 1:
            first_status = final_status = lines[0]
        else:
            first_status = lines[0]
            final_status = lines[-1]
            self.assertIn("'status': 'running'", first_status)
            self.assertIn("'id': 2", first_status)
        self.assertIn("'id': 2", first_status)
        self.assertIn("'status': 'finished'", final_status)
        self.assertIn("'stdout': b'avocado'", final_status)
        self.assertEqual(res.exit_status, exit_codes.AVOCADO_ALL_OK)

    @unittest.skipUnless(os.path.exists('/bin/sleep'),
                         ('Executable "/bin/sleep" used in recipe is not '
                          'available in the system'))
    def test_recipe_exec_3(self):
        recipe = os.path.join(BASEDIR, "examples", "recipes", "tasks", "exec",
                              "3-sleep.json")
        cmd = "%s task-run-recipe %s" % (AVOCADO, recipe)
        res = process.run(cmd, ignore_status=True)
        lines = res.stdout_text.splitlines()
        # based on the :data:`avocado.core.nrunner.RUNNER_RUN_STATUS_INTERVAL`
        # this runnable should produce multiple status lines
        self.assertGreater(len(lines), 1)
        first_status = lines[0]
        self.assertIn("'status': 'running'", first_status)
        self.assertIn("'id': 3", first_status)
        final_status = lines[-1]
        self.assertIn("'id': 3", first_status)
        self.assertIn("'status': 'finished'", final_status)
        self.assertEqual(res.exit_status, exit_codes.AVOCADO_ALL_OK)
