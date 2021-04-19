import os
import sys
import unittest

from avocado.utils import process, script
from selftests.utils import BASEDIR, TestCaseTmpDir

UNITTEST_GOOD = """from avocado import Test
from unittest import main


class CustomBaselogDirInit(Test):
    def __init__(self, *args, **kwargs):
        super(CustomBaselogDirInit, self).__init__(base_logdir="%s", *args,
                                                   **kwargs)

class AvocadoPassTest(CustomBaselogDirInit):
    def test(self):
        self.assertTrue(True)
if __name__ == '__main__':
    main()
"""

UNITTEST_FAIL = """from avocado import Test
from unittest import main


class CustomBaselogDirInit(Test):
    def __init__(self, *args, **kwargs):
        super(CustomBaselogDirInit, self).__init__(base_logdir="%s", *args,
                                                   **kwargs)

class AvocadoFailTest(CustomBaselogDirInit):
    def test(self):
        self.fail('This test is supposed to fail')
if __name__ == '__main__':
    main()
"""

UNITTEST_ERROR = """from avocado import Test
from unittest import main


class CustomBaselogDirInit(Test):
    def __init__(self, *args, **kwargs):
        super(CustomBaselogDirInit, self).__init__(base_logdir="%s", *args,
                                                   **kwargs)

class AvocadoErrorTest(CustomBaselogDirInit):
    def test(self):
        self.error('This test is supposed to error')
if __name__ == '__main__':
    main()
"""


class UnittestCompat(TestCaseTmpDir):

    def setUp(self):
        super(UnittestCompat, self).setUp()
        self.original_pypath = os.environ.get('PYTHONPATH')
        if self.original_pypath is not None:
            os.environ['PYTHONPATH'] = '%s:%s' % (
                BASEDIR, self.original_pypath)
        else:
            os.environ['PYTHONPATH'] = '%s' % BASEDIR
        self.unittest_script_good = script.TemporaryScript(
            'unittest_good.py',
            UNITTEST_GOOD % self.tmpdir.name,
            'avocado_as_unittest_functional')
        self.unittest_script_good.save()
        self.unittest_script_fail = script.TemporaryScript(
            'unittest_fail.py',
            UNITTEST_FAIL % self.tmpdir.name,
            'avocado_as_unittest_functional')
        self.unittest_script_fail.save()
        self.unittest_script_error = script.TemporaryScript(
            'unittest_error.py',
            UNITTEST_ERROR % self.tmpdir.name,
            'avocado_as_unittest_functional')
        self.unittest_script_error.save()

    def test_run_pass(self):
        cmd_line = '%s %s' % (sys.executable, self.unittest_script_good)
        result = process.run(cmd_line)
        self.assertEqual(0, result.exit_status)
        self.assertIn(b'Ran 1 test in', result.stderr)

    def test_run_fail(self):
        cmd_line = '%s %s' % (sys.executable, self.unittest_script_fail)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(1, result.exit_status)
        self.assertIn(b'Ran 1 test in', result.stderr)
        self.assertIn(b'This test is supposed to fail', result.stderr)
        self.assertIn(b'FAILED (failures=1)', result.stderr)

    def test_run_error(self):
        cmd_line = '%s %s' % (sys.executable, self.unittest_script_error)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(1, result.exit_status)
        self.assertIn(b'Ran 1 test in', result.stderr)
        self.assertIn(b'This test is supposed to error', result.stderr)
        self.assertIn(b'FAILED (errors=1)', result.stderr)

    def tearDown(self):
        super(UnittestCompat, self).tearDown()
        self.unittest_script_error.remove()
        self.unittest_script_fail.remove()
        self.unittest_script_good.remove()


if __name__ == '__main__':
    unittest.main()
