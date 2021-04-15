import glob
import os
import unittest
import xml.dom.minidom

from avocado.core import exit_codes
from avocado.utils import genio, process, script
from selftests.utils import (AVOCADO, BASEDIR, TestCaseTmpDir,
                             skipOnLevelsInferiorThan)

SCRIPT_CONTENT = """#!/bin/bash
sleep 2
"""

PYTHON_CONTENT = """#!/usr/bin/env python
import time
from avocado import Test

class Dummy(Test):
    def test00sleep(self):
        time.sleep(10)
    def test01pass(self):
        pass
    def test02pass(self):
        pass
"""


class ParseXMLError(Exception):
    pass


class JobTimeOutTest(TestCaseTmpDir):

    def setUp(self):
        super(JobTimeOutTest, self).setUp()
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

    def run_and_check(self, cmd_line, e_rc, e_ntests, e_nerrors, e_nfailures,
                      e_nskip):
        os.chdir(BASEDIR)
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
        res_dir = os.path.join(self.tmpdir.name, "latest", "test-results")
        debug_log_paths = glob.glob(os.path.join(res_dir, "%s-*" % idx, "debug.log"))
        debug_log = genio.read_file(debug_log_paths[0])
        self.assertIn("Runner error occurred: Timeout reached", debug_log,
                      "Runner error occurred: Timeout reached message not "
                      "in the %sst test's debug.log:\n%s"
                      % (idx, debug_log))
        self.assertIn("Traceback (most recent call last)", debug_log,
                      "Traceback not present in the %sst test's debug.log:\n%s"
                      % (idx, debug_log))

    @skipOnLevelsInferiorThan(1)
    def test_sleep_longer_timeout(self):
        """:avocado: tags=parallel:1"""
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    '--xunit - --job-timeout=5 %s examples/tests/passtest.py' %
                    (AVOCADO, self.tmpdir.name, self.script.path))
        self.run_and_check(cmd_line, 0, 2, 0, 0, 0)

    def test_sleep_short_timeout(self):
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    '--xunit - --job-timeout=1 %s examples/tests/passtest.py' %
                    (AVOCADO, self.tmpdir.name, self.script.path))
        self.run_and_check(cmd_line, exit_codes.AVOCADO_JOB_INTERRUPTED,
                           2, 1, 0, 1)
        self._check_timeout_msg(1)

    def test_sleep_short_timeout_with_test_methods(self):
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    '--xunit - --job-timeout=1 %s' %
                    (AVOCADO, self.tmpdir.name, self.py.path))
        self.run_and_check(cmd_line, exit_codes.AVOCADO_JOB_INTERRUPTED,
                           3, 1, 0, 2)
        self._check_timeout_msg(1)

    def test_invalid_values(self):
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    '--job-timeout=1,5 examples/tests/passtest.py'
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
        self.assertIn(b'invalid time_to_seconds value', result.stderr)
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    '--job-timeout=123x examples/tests/passtest.py'
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
        self.assertIn(b'invalid time_to_seconds', result.stderr)

    def test_valid_values(self):
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    '--job-timeout=123 examples/tests/passtest.py'
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    '--job-timeout=123s examples/tests/passtest.py'
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    '--job-timeout=123m examples/tests/passtest.py'
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    '--job-timeout=123h examples/tests/passtest.py'
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)

    def tearDown(self):
        super(JobTimeOutTest, self).tearDown()
        self.script.remove()
        self.py.remove()


if __name__ == '__main__':
    unittest.main()
