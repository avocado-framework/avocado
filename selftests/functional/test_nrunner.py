import os
import sys
import unittest

from avocado.core.job import Job
from avocado.utils import process
from selftests.utils import AVOCADO, TestCaseTmpDir, skipUnlessPathExists

RUNNER = "%s -m avocado.core.nrunner" % sys.executable


class NRunnerFeatures(unittest.TestCase):
    @skipUnlessPathExists('/bin/false')
    def test_custom_exit_codes(self):
        config = {'run.references': ['/bin/false'],
                  'run.test_runner': 'nrunner',
                  'runner.exectest.exitcodes.skip': [1],
                  'run.keep_tmp': True}
        with Job.from_config(job_config=config) as job:
            self.assertEqual(job.run(), 0)

    @skipUnlessPathExists('/bin/false')
    @skipUnlessPathExists('/bin/true')
    def test_failfast(self):
        config = {'run.references': ['/bin/true',
                                     '/bin/false',
                                     '/bin/true',
                                     '/bin/true'],
                  'run.test_runner': 'nrunner',
                  'run.failfast': True,
                  'nrunner.shuffle': False,
                  'nrunner.max_parallel_tasks': 1}
        with Job.from_config(job_config=config) as job:
            self.assertEqual(job.run(), 9)
            self.assertEqual(job.result.passed, 1)
            self.assertEqual(job.result.errors, 0)
            self.assertEqual(job.result.failed, 1)
            self.assertEqual(job.result.skipped, 2)


class RunnableRun(unittest.TestCase):

    def test_noop(self):
        res = process.run("%s runnable-run -k noop" % RUNNER,
                          ignore_status=True)
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'time': ", res.stdout)
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


class TaskRun(unittest.TestCase):

    def test_noop(self):
        res = process.run("%s task-run -i XXXno-opXXX -k noop" % RUNNER,
                          ignore_status=True)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'id': 'XXXno-opXXX'", res.stdout)
        self.assertEqual(res.exit_status, 0)


class ResolveSerializeRun(TestCaseTmpDir):
    @skipUnlessPathExists('/bin/true')
    def test(self):
        cmd = "%s list --write-recipes-to-directory=%s -- /bin/true"
        cmd %= (AVOCADO, self.tmpdir.name)
        res = process.run(cmd)
        self.assertEqual(b'exec-test /bin/true\n', res.stdout)
        cmd = "%s runnable-run-recipe %s"
        cmd %= (RUNNER, os.path.join(self.tmpdir.name, '1.json'))
        res = process.run(cmd)
        self.assertIn(b"'status': 'finished'", res.stdout)
