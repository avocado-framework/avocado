import os
import sys
import unittest

from avocado.core import exit_codes
from avocado.utils import process, astring

from .. import BASEDIR


PY_CMD = sys.executable


class StandaloneTests(unittest.TestCase):

    def setUp(self):
        self.original_pypath = os.environ.get('PYTHONPATH')
        if self.original_pypath is not None:
            os.environ['PYTHONPATH'] = '%s:%s' % (BASEDIR, self.original_pypath)
        else:
            os.environ['PYTHONPATH'] = '%s' % BASEDIR

    def run_and_check(self, cmd_line, expected_rc, tstname):
        os.chdir(BASEDIR)
        result = process.run(cmd_line, ignore_status=True,
                             encoding=astring.ENCODING)
        self.assertEqual(result.exit_status, expected_rc,
                         "Stand alone %s did not return rc "
                         "%d:\n%s" % (tstname, expected_rc, result))
        return result

    def test_passtest(self):
        cmd_line = '%s ./examples/tests/passtest.py -r' % PY_CMD
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc, 'passtest')

    def test_warntest(self):
        cmd_line = '%s ./examples/tests/warntest.py -r' % PY_CMD
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc, 'warntest')

    def test_failtest(self):
        cmd_line = '%s ./examples/tests/failtest.py -r' % PY_CMD
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.run_and_check(cmd_line, expected_rc, 'failtest')

    def test_errortest_nasty(self):
        cmd_line = '%s ./examples/tests/errortest_nasty.py -r' % PY_CMD
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        result = self.run_and_check(cmd_line, expected_rc, 'errortest_nasty')
        if sys.version_info[0] == 3:
            exc = u"errortest_nasty.NastyException: Nasty-string-like-exception\u017e"
        else:
            exc = u"NastyException: Nasty-string-like-exception\\u017e"
        count = result.stdout_text.count(u"\n%s" % exc)
        self.assertEqual(count, 2, "Exception \\n%s should be present twice in"
                         "the log (once from the log, second time when parsing"
                         "exception details." % (exc))

    def test_errortest_nasty2(self):
        cmd_line = '%s ./examples/tests/errortest_nasty2.py -r' % PY_CMD
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        result = self.run_and_check(cmd_line, expected_rc, 'errortest_nasty2')
        self.assertIn(b"Exception: Unable to get exception, check the traceback"
                      b" for details.", result.stdout)

    def test_errortest_nasty3(self):
        cmd_line = '%s ./examples/tests/errortest_nasty3.py -r' % PY_CMD
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        result = self.run_and_check(cmd_line, expected_rc, 'errortest_nasty3')
        if sys.version_info[0] == 3:
            exc = b"TypeError: exceptions must derive from BaseException"
        else:
            exc = b"TestError: <errortest_nasty3.NastyException instance at "
        self.assertIn(exc, result.stdout)

    def test_errortest(self):
        cmd_line = '%s ./examples/tests/errortest.py -r' % PY_CMD
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.run_and_check(cmd_line, expected_rc, 'errortest')


if __name__ == '__main__':
    unittest.main()
