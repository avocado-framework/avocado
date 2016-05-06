import glob
import os
import sys
import tempfile
import shutil
import xml.dom.minidom

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import exit_codes
from avocado.utils import process
from avocado.utils import script


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


SCRIPT_CONTENT = """#!/bin/bash
sleep 2
"""

PYTHON_CONTENT = """#!/usr/bin/env python
import time
from avocado import Test

class Dummy(Test):
    def test00sleep(self):
        time.sleep(2)
    def test01pass(self):
        pass
    def test02pass(self):
        pass
"""


class ParseXMLError(Exception):
    pass


class JobTimeOutTest(unittest.TestCase):

    def setUp(self):
        self.script = script.TemporaryScript(
            'sleep.sh',
            SCRIPT_CONTENT,
            'avocado_timeout_functional')
        self.script.save()
        self.py = script.TemporaryScript(
            'sleep_test.py',
            PYTHON_CONTENT,
            'avocado_timeout_functional')
        self.py.save()
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        os.chdir(basedir)

    def run_and_check(self, cmd_line, e_rc, e_ntests, e_nerrors, e_nfailures,
                      e_nskip):
        os.chdir(basedir)
        result = process.run(cmd_line, ignore_status=True)
        xml_output = result.stdout
        self.assertEqual(result.exit_status, e_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (e_rc, result))
        try:
            xunit_doc = xml.dom.minidom.parseString(xml_output)
        except Exception as detail:
            raise ParseXMLError("Failed to parse content: %s\n%s" %
                                (detail, xml_output))

        testsuite_list = xunit_doc.getElementsByTagName('testsuite')
        self.assertEqual(len(testsuite_list), 1, 'More than one testsuite tag')

        testsuite_tag = testsuite_list[0]
        self.assertEqual(len(testsuite_tag.attributes), 7,
                         'The testsuite tag does not have 7 attributes. '
                         'XML:\n%s' % xml_output)

        n_tests = int(testsuite_tag.attributes['tests'].value)
        self.assertEqual(n_tests, e_ntests,
                         "Unexpected number of executed tests, "
                         "XML:\n%s" % xml_output)

        n_errors = int(testsuite_tag.attributes['errors'].value)
        self.assertEqual(n_errors, e_nerrors,
                         "Unexpected number of test errors, "
                         "XML:\n%s" % xml_output)

        n_failures = int(testsuite_tag.attributes['failures'].value)
        self.assertEqual(n_failures, e_nfailures,
                         "Unexpected number of test failures, "
                         "XML:\n%s" % xml_output)

        n_skip = int(testsuite_tag.attributes['skipped'].value)
        self.assertEqual(n_skip, e_nskip,
                         "Unexpected number of test skips, "
                         "XML:\n%s" % xml_output)

    def _check_timeout_msg(self, idx):
        res_dir = os.path.join(self.tmpdir, "latest", "test-results")
        debug_log = glob.glob(os.path.join(res_dir, "%s-*" % idx, "debug.log"))
        debug_log = open(debug_log[0]).read()
        self.assertIn("RUNNER: Timeout reached", debug_log, "RUNNER: Timeout "
                      "reached message not in the %sst test's debug.log:\n%s"
                      % (idx, debug_log))
        self.assertIn("Traceback (most recent call last)", debug_log,
                      "Traceback not present in the %sst test's debug.log:\n%s"
                      % (idx, debug_log))

    def test_sleep_longer_timeout(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--xunit - --job-timeout=5 %s examples/tests/passtest.py' %
                    (self.tmpdir, self.script.path))
        self.run_and_check(cmd_line, 0, 2, 0, 0, 0)

    def test_sleep_short_timeout(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--xunit - --job-timeout=1 %s examples/tests/passtest.py' %
                    (self.tmpdir, self.script.path))
        self.run_and_check(cmd_line, exit_codes.AVOCADO_JOB_INTERRUPTED,
                           2, 1, 0, 1)
        self._check_timeout_msg(1)

    def test_sleep_short_timeout_with_test_methods(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--xunit - --job-timeout=1 %s' %
                    (self.tmpdir, self.py.path))
        self.run_and_check(cmd_line, exit_codes.AVOCADO_JOB_INTERRUPTED,
                           3, 1, 0, 2)
        self._check_timeout_msg(1)

    def test_invalid_values(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--job-timeout=0 examples/tests/passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
        self.assertIn('Invalid number', result.stderr)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--job-timeout=123x examples/tests/passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
        self.assertIn('Invalid number', result.stderr)

    def test_valid_values(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--job-timeout=123 examples/tests/passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--job-timeout=123s examples/tests/passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--job-timeout=123m examples/tests/passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--job-timeout=123h examples/tests/passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)

    def tearDown(self):
        self.script.remove()
        self.py.remove()
        shutil.rmtree(self.tmpdir)

if __name__ == '__main__':
    unittest.main()
