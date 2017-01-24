import os
import sys
import shutil
import tempfile

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import exit_codes
from avocado.utils import script
from avocado.utils import process

basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)

AVOCADO_EXTERNAL_LIB = """
def cleanup_function(arg1):
    print('Bogus cleanup function. arg1: %s' % arg1)
"""

AVOCADO_TEST_RUNNER_QUEUE_EXTERNAL_LIB = """#!/usr/bin/env python
from avocado import Test
from avocado.utils import runtime as avocado_runtime
from avocado_queue_testlib import cleanup_function


class AvocadoQueueTests(Test):
    def test_stuff_add_cleanup(self):
        avocado_runtime.CURRENT_TEST.runner_queue.put({'func_at_exit': cleanup_function,
                                                       'args': ('Hello Avocado Test Queue!',),
                                                       'once': True})
        self.assertEqual(1, 1)
"""


class TestRunnerQueue(unittest.TestCase):
    def setUp(self):
        os.chdir(basedir)
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def test_runner_queue_external_lib(self):
        mylib = script.TemporaryScript(
            'avocado_queue_testlib.py',
            AVOCADO_EXTERNAL_LIB,
            'avocado_runner_queue_functional',
            0644)
        mylib.save()
        mytest = script.Script(
            os.path.join(os.path.dirname(mylib.path), 'test.py'),
            AVOCADO_TEST_RUNNER_QUEUE_EXTERNAL_LIB)
        os.chdir(basedir)
        mytest.save()
        # job should be able to finish under 5 seconds. If this fails, it's
        # possible that we hit the "simple test fork bomb" bug
        cmd_line = ['./scripts/avocado',
                    'run',
                    '--sysinfo=off',
                    '--job-results-dir',
                    "%s" % self.tmpdir,
                    "%s" % mytest]
        result = process.run(' '.join(cmd_line))
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertIn('Bogus cleanup function. arg1: Hello Avocado Test Queue!',
                      result.stdout,
                      'Cleanup function message not found in stdout:\n%s' %
                      result.stdout)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
