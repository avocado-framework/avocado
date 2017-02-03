import os
import unittest

from avocado.core import exit_codes
from avocado.utils import process


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


class StandaloneTests(unittest.TestCase):

    def setUp(self):
        self.original_pypath = os.environ.get('PYTHONPATH')
        if self.original_pypath is not None:
            os.environ['PYTHONPATH'] = '%s:%s' % (basedir, self.original_pypath)
        else:
            os.environ['PYTHONPATH'] = '%s' % basedir

    def run_and_check(self, cmd_line, expected_rc, tstname):
        os.chdir(basedir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Stand alone %s did not return rc "
                         "%d:\n%s" % (tstname, expected_rc, result))
        return result

    def test_passtest(self):
        cmd_line = './examples/tests/passtest.py -r'
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc, 'passtest')

    def test_warntest(self):
        cmd_line = './examples/tests/warntest.py -r'
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc, 'warntest')

    def test_failtest(self):
        cmd_line = './examples/tests/failtest.py -r'
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.run_and_check(cmd_line, expected_rc, 'failtest')

    def test_errortest_nasty(self):
        cmd_line = './examples/tests/errortest_nasty.py -r'
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        result = self.run_and_check(cmd_line, expected_rc, 'errortest_nasty')
        exc = "NastyException: Nasty-string-like-exception"
        count = result.stdout.count("\n%s" % exc)
        self.assertEqual(count, 2, "Exception \\n%s should be present twice in"
                         "the log (once from the log, second time when parsing"
                         "exception details." % (exc))

    def test_errortest_nasty2(self):
        cmd_line = './examples/tests/errortest_nasty2.py -r'
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        result = self.run_and_check(cmd_line, expected_rc, 'errortest_nasty2')
        self.assertIn("Exception: Unable to get exception, check the traceback"
                      " for details.", result.stdout)

    def test_errortest_nasty3(self):
        cmd_line = './examples/tests/errortest_nasty3.py -r'
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        result = self.run_and_check(cmd_line, expected_rc, 'errortest_nasty3')
        self.assertIn("TestError: <errortest_nasty3.NastyException instance at ",
                      result.stdout)

    def test_errortest(self):
        cmd_line = './examples/tests/errortest.py -r'
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.run_and_check(cmd_line, expected_rc, 'errortest')


if __name__ == '__main__':
    unittest.main()
