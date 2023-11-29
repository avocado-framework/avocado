import glob
import os
import tempfile
import unittest
import xml.dom.minidom

from avocado.core import exit_codes
from avocado.utils import genio, process, script
from selftests.utils import AVOCADO, BASEDIR, TestCaseTmpDir

SCRIPT_SHORT_CONTENT = """#!/bin/bash
sleep 2
"""

SCRIPT_LONG_CONTENT = """#!/bin/bash
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

    def tearDown(self):
        self.log.info("tearDown")
"""

PYTHON_LONG_CONTENT = """#!/usr/bin/env python
import time
from avocado import Test

class Dummy(Test):
    def test00sleep(self):
        time.sleep(10)

    def tearDown(self):
        time.sleep(5)
        self.log.info("tearDown")
"""


class ParseXMLError(Exception):
    pass


class JobTimeOutTest(TestCaseTmpDir):
    def setUp(self):
        super().setUp()
        self.script_short = script.TemporaryScript(
            "sleep_short.sh", SCRIPT_SHORT_CONTENT, "avocado_timeout_functional"
        )
        self.script_short.save()
        self.script_long = script.TemporaryScript(
            "sleep_long.sh", SCRIPT_LONG_CONTENT, "avocado_timeout_functional"
        )
        self.script_long.save()
        self.py = script.TemporaryScript(
            "sleep_test.py", PYTHON_CONTENT, "avocado_timeout_functional"
        )
        self.py.save()
        self.long_py = script.TemporaryScript(
            "sleep_long.py", PYTHON_LONG_CONTENT, "avocado_timeout_functional"
        )
        self.long_py.save()

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

    def _check_timeout_msg(self, idx, message, negation=False):
        res_dir = os.path.join(self.tmpdir.name, "latest", "test-results")
        debug_log_paths = glob.glob(os.path.join(res_dir, f"{idx}-*", "debug.log"))
        debug_log = genio.read_file(debug_log_paths[0])
        if not negation:
            self.assertIn(
                message,
                debug_log,
                f"{message} message not in the {idx}st test's debug.log:\n{debug_log}",
            )
        else:
            self.assertNotIn(
                message,
                debug_log,
                f"{message} message is in the {idx}st test's debug.log:\n{debug_log}",
            )

    def test_sleep_short_timeout(self):
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo "
            f"--job-timeout=1 {self.script_long.path} "
            f"examples/tests/passtest.py"
        )
        self.run_and_check(cmd_line, exit_codes.AVOCADO_JOB_INTERRUPTED, 2, [])

    def test_sleep_longer_timeout_interrupted(self):
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo "
            f"--job-timeout=5 {self.script_long.path} "
            f"examples/tests/passtest.py"
        )
        self.run_and_check(
            cmd_line, exit_codes.AVOCADO_JOB_INTERRUPTED, 2, [self.script_long.path]
        )
        self._check_timeout_msg(1, "Test interrupted: Timeout reached")

    def test_sleep_longer_timeout_all_ok(self):
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo "
            f"--job-timeout=10 {self.script_short.path} "
            f"examples/tests/passtest.py"
        )
        self.run_and_check(cmd_line, exit_codes.AVOCADO_ALL_OK, 2, [])

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
        self._check_timeout_msg(1, "Test interrupted: Timeout reached")

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

    def test_timeout_with_tear_down(self):
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
        self._check_timeout_msg(1, "tearDown")

    def test_timeout_with_long_tear_down(self):
        config = "[runner.task.interval]\nfrom_soft_to_hard_termination=10\n"
        fd, config_file = tempfile.mkstemp(dir=self.tmpdir.name)
        os.write(fd, config.encode())
        os.close(fd)
        cmd_line = (
            f"{AVOCADO} --config {config_file} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo "
            f"--job-timeout=5 {self.long_py.path}"
        )
        self.run_and_check(
            cmd_line,
            exit_codes.AVOCADO_JOB_INTERRUPTED,
            1,
            [f"{self.long_py.path}:Dummy.test00sleep"],
        )
        self._check_timeout_msg(1, "tearDown")

    def test_timeout_with_long_tear_down_interupted(self):
        config = "[runner.task.interval]\nfrom_soft_to_hard_termination=3\n"
        fd, config_file = tempfile.mkstemp(dir=self.tmpdir.name)
        os.write(fd, config.encode())
        os.close(fd)
        cmd_line = (
            f"{AVOCADO} --config {config_file} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo "
            f"--job-timeout=5 {self.long_py.path}"
        )
        self.run_and_check(
            cmd_line,
            exit_codes.AVOCADO_JOB_INTERRUPTED,
            1,
            [f"{self.long_py.path}:Dummy.test00sleep"],
        )
        self._check_timeout_msg(1, "tearDown", True)

    def tearDown(self):
        super().tearDown()
        self.script_short.remove()
        self.script_long.remove()
        self.py.remove()
        self.long_py.remove()


if __name__ == "__main__":
    unittest.main()
