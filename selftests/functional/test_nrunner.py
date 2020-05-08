import os
import sys
import unittest
import tempfile

from .. import AVOCADO, BASEDIR, temp_dir_prefix

from avocado.utils import process


RUNNER = "%s -m avocado.core.nrunner" % sys.executable


class RunnableRun(unittest.TestCase):

    def test_noop(self):
        res = process.run("%s runnable-run -k noop" % RUNNER,
                          ignore_status=True)
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'time': ", res.stdout)
        self.assertEqual(res.exit_status, 0)

    def test_exec(self):
        # 'base64:LWM=' becomes '-c' and makes Python execute the
        # commands on the subsequent argument
        cmd = ("%s runnable-run -k exec -u %s -a 'base64:LWM=' -a "
               "'import sys; sys.exit(99)'" % (RUNNER, sys.executable))
        res = process.run(cmd, ignore_status=True)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'returncode': 99", res.stdout)
        self.assertEqual(res.exit_status, 0)

    @unittest.skipUnless(os.path.exists('/bin/echo'),
                         ('Executable "/bin/echo" used in test is not '
                          'available in the system'))
    def test_exec_echo(self):
        # 'base64:LW4=' becomes '-n' and prevents echo from printing a newline
        cmd = ("%s runnable-run -k exec -u /bin/echo -a 'base64:LW4=' -a "
               "_Avocado_Runner_" % RUNNER)
        res = process.run(cmd, ignore_status=True)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'stdout': b'_Avocado_Runner_'", res.stdout)
        self.assertIn(b"'returncode': 0", res.stdout)
        self.assertEqual(res.exit_status, 0)

    @unittest.skipUnless(os.path.exists('/bin/sh'),
                         ('Executable "/bin/sh" used in recipe is not '
                          'available in the system'))
    @unittest.skipUnless(os.path.exists('/bin/echo'),
                         ('Executable "/bin/echo" used in recipe is not '
                          'available in the system'))
    def test_recipe(self):
        recipe = os.path.join(BASEDIR, "examples", "nrunner", "recipes",
                              "runnables", "exec_sh_echo_env_var.json")
        cmd = "%s runnable-run-recipe %s" % (RUNNER, recipe)
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
        self.assertIn("'stdout': b'Hello world!\\n'", final_status)
        self.assertIn("'time': ", final_status)
        self.assertEqual(res.exit_status, 0)

    def test_noop_valid_kwargs(self):
        res = process.run("%s runnable-run -k noop foo=bar" % RUNNER,
                          ignore_status=True)
        self.assertEqual(res.exit_status, 0)

    def test_noop_invalid_kwargs(self):
        res = process.run("%s runnable-run -k noop foo" % RUNNER,
                          ignore_status=True)
        self.assertIn(b'Invalid keyword parameter: "foo"', res.stderr)
        self.assertEqual(res.exit_status, 2)

    @unittest.skipUnless(os.path.exists('/bin/env'),
                         ('Executable "/bin/env" used in test is not '
                          'available in the system'))
    def test_exec_kwargs(self):
        res = process.run("%s runnable-run -k exec -u /bin/env X=Y" % RUNNER,
                          ignore_status=True)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"X=Y\\n", res.stdout)
        self.assertEqual(res.exit_status, 0)


class TaskRun(unittest.TestCase):

    def test_noop(self):
        res = process.run("%s task-run -i XXXno-opXXX -k noop" % RUNNER,
                          ignore_status=True)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'id': 'XXXno-opXXX'", res.stdout)
        self.assertEqual(res.exit_status, 0)

    @unittest.skipUnless(os.path.exists('/bin/uname'),
                         ('Executable "/bin/uname" used in recipe is not '
                          'available in the system'))
    def test_recipe_exec_1(self):
        recipe = os.path.join(BASEDIR, "examples", "nrunner", "recipes",
                              "tasks", "exec", "1-uname.json")
        cmd = "%s task-run-recipe %s" % (RUNNER, recipe)
        res = process.run(cmd, ignore_status=True)
        lines = res.stdout_text.splitlines()
        if len(lines) == 1:
            first_status = final_status = lines[0]
        else:
            first_status = lines[0]
            final_status = lines[-1]
            self.assertIn("'status': 'started'", first_status)
            self.assertIn("'id': 1", first_status)
        self.assertIn("'id': 1", first_status)
        self.assertIn("'status': 'finished'", final_status)
        self.assertEqual(res.exit_status, 0)

    @unittest.skipUnless(os.path.exists('/bin/echo'),
                         ('Executable "/bin/echo" used in recipe is not '
                          'available in the system'))
    def test_recipe_exec_2(self):
        recipe = os.path.join(BASEDIR, "examples", "nrunner", "recipes",
                              "tasks", "exec", "2-echo.json")
        cmd = "%s task-run-recipe %s" % (RUNNER, recipe)
        res = process.run(cmd, ignore_status=True)
        lines = res.stdout_text.splitlines()
        if len(lines) == 1:
            first_status = final_status = lines[0]
        else:
            first_status = lines[0]
            final_status = lines[-1]
            self.assertIn("'status': 'started'", first_status)
            self.assertIn("'id': 2", first_status)
        self.assertIn("'id': 2", first_status)
        self.assertIn("'status': 'finished'", final_status)
        self.assertIn("'stdout': b'avocado'", final_status)
        self.assertEqual(res.exit_status, 0)

    @unittest.skipUnless(os.path.exists('/bin/sleep'),
                         ('Executable "/bin/sleep" used in recipe is not '
                          'available in the system'))
    def test_recipe_exec_3(self):
        recipe = os.path.join(BASEDIR, "examples", "nrunner", "recipes",
                              "tasks", "exec", "3-sleep.json")
        cmd = "%s task-run-recipe %s" % (RUNNER, recipe)
        res = process.run(cmd, ignore_status=True)
        lines = res.stdout_text.splitlines()
        # based on the :data:`avocado.core.nrunner.RUNNER_RUN_STATUS_INTERVAL`
        # this runnable should produce multiple status lines
        self.assertGreater(len(lines), 1)
        first_status = lines[0]
        self.assertIn("'status': 'started'", first_status)
        self.assertIn("'id': 3", first_status)
        final_status = lines[-1]
        self.assertIn("'id': 3", first_status)
        self.assertIn("'status': 'finished'", final_status)
        self.assertEqual(res.exit_status, 0)


class ResolveSerializeRun(unittest.TestCase):
    @unittest.skipUnless(os.path.exists('/bin/true'),
                         ('Executable "/bin/true" used in test'))
    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    def test(self):
        cmd = "%s nlist --write-recipes-to-directory=%s -- /bin/true"
        cmd %= (AVOCADO, self.tmpdir.name)
        res = process.run(cmd)
        self.assertEqual(b'exec-test /bin/true\n', res.stdout)
        cmd = "%s runnable-run-recipe %s"
        cmd %= (RUNNER, os.path.join(self.tmpdir.name, '1.json'))
        res = process.run(cmd)
        self.assertIn(b"'status': 'finished'", res.stdout)

    def tearDown(self):
        self.tmpdir.cleanup()
