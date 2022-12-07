import glob
import os
import unittest
import xml.dom.minidom

from avocado.core import exit_codes
from avocado.utils import genio, process, script
from selftests.utils import AVOCADO, BASEDIR, TestCaseTmpDir, skipOnLevelsInferiorThan

SCRIPT_CONTENT = """#!/bin/bash
sleep 10
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
        super().setUp()
        self.script = script.TemporaryScript(
            "sleep.sh", SCRIPT_CONTENT, "avocado_timeout_functional"
        )
        self.script.save()
        self.py = script.TemporaryScript(
            "sleep_test.py", PYTHON_CONTENT, "avocado_timeout_functional"
        )
        self.py.save()

    def run_and_check(self, cmd_line, e_rc, e_ntests, terminated_tests):
        os.chdir(BASEDIR)
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout_text
        xml_output = os.path.join(self.tmpdir.name, "latest", "results.xml")
        self.assertEqual(
            result.exit_status, e_rc, f"Avocado did not return rc {e_rc}:\n{result}"
        )
        try:
            xunit_doc = xml.dom.minidom.parse(xml_output)
        except Exception as detail:
            raise ParseXMLError(f"Failed to parse content: {detail}\n" f"{xml_output}")

        testsuite_list = xunit_doc.getElementsByTagName("testsuite")
        self.assertEqual(len(testsuite_list), 1, "More than one testsuite tag")

        testsuite_tag = testsuite_list[0]
        self.assertEqual(
            len(testsuite_tag.attributes),
            7,
            (f"The testsuite tag does not have 7 attributes. " f"XML:\n{xml_output}"),
        )

        n_tests = int(testsuite_tag.attributes["tests"].value)
        self.assertEqual(
            n_tests,
            e_ntests,
            (f"Unexpected number of executed tests, XML:\n" f"{xml_output}"),
        )

        n_failures = int(testsuite_tag.attributes["failures"].value)
        self.assertEqual(
            n_failures,
            0,
            (f"Unexpected number of test failures, XML:\n" f"{xml_output}"),
        )

        e_skip = e_ntests - output.count("STARTED")
        n_skip = int(testsuite_tag.attributes["skipped"].value)
        self.assertEqual(
            n_skip,
            e_skip,
            (f"Unexpected number of test skips, XML:\n" f"{xml_output}"),
        )
        for terminated_test in terminated_tests:
            self.assertTrue(
                f"{terminated_test}:  INTERRUPTED: Test interrupted: Timeout reached"
                in output,
                f"Test {terminated_test} was not in {output}.",
            )

    def _check_timeout_msg(self, idx):
        res_dir = os.path.join(self.tmpdir.name, "latest", "test-results")
        debug_log_paths = glob.glob(os.path.join(res_dir, f"{idx}-*", "debug.log"))
        debug_log = genio.read_file(debug_log_paths[0])
        self.assertIn(
            "Runner error occurred: Timeout reached",
            debug_log,
            (
                f"Runner error occurred: Timeout reached message not "
                f"in the {idx}st test's debug.log:\n{debug_log}"
            ),
        )

    @skipOnLevelsInferiorThan(1)
    def test_sleep_longer_timeout(self):
        """:avocado: tags=parallel:1"""
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo "
            f"--job-timeout=5 {self.script.path} "
            f"examples/tests/passtest.py"
        )
        self.run_and_check(cmd_line, 0, 2, [])

    def test_sleep_short_timeout(self):
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo "
            f"--job-timeout=5 {self.script.path} "
            f"examples/tests/passtest.py"
        )
        self.run_and_check(
            cmd_line, exit_codes.AVOCADO_JOB_INTERRUPTED, 2, [self.script.path]
        )
        self._check_timeout_msg(1)

    def test_sleep_short_timeout_with_test_methods(self):
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo "
            f"--job-timeout=5 {self.py.path}"
        )
        self.run_and_check(
            cmd_line,
            exit_codes.AVOCADO_JOB_INTERRUPTED,
            3,
            [f"{self.py.path}:Dummy.test00sleep"],
        )
        self._check_timeout_msg(1)

    def test_invalid_values(self):
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo --job-timeout=1,5 "
            f"examples/tests/passtest.py"
        )
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
        self.assertIn(b"invalid time_to_seconds value", result.stderr)
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo --job-timeout=123x "
            f"examples/tests/passtest.py"
        )
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
        self.assertIn(b"invalid time_to_seconds", result.stderr)

    def test_valid_values(self):
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo --job-timeout=123 "
            f"examples/tests/passtest.py"
        )
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo --job-timeout=123s "
            f"examples/tests/passtest.py"
        )
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo --job-timeout=123m "
            f"examples/tests/passtest.py"
        )
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo --job-timeout=123h "
            f"examples/tests/passtest.py"
        )
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)

    def tearDown(self):
        super().tearDown()
        self.script.remove()
        self.py.remove()


if __name__ == "__main__":
    unittest.main()
