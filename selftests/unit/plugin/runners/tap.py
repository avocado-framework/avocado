import os
import tempfile
import unittest

from avocado.core.nrunner.runnable import Runnable
from avocado.plugins.runners import tap as runner_tap
from selftests.utils import skipUnlessPathExists, temp_dir_prefix


class RunnerTap(unittest.TestCase):
    def setUp(self):
        prefix = temp_dir_prefix(self)
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    @skipUnlessPathExists("/bin/sh")
    def test_fail(self):
        tap_script = """#!/bin/sh
echo '1..2'
echo '# Defining a basic test'
echo 'ok 1 - description 1'
echo 'not ok 2 - description 2'"""
        tap_path = os.path.join(self.tmpdir.name, "tap.sh")

        with open(tap_path, "w", encoding="utf-8") as fp:
            fp.write(tap_script)

        runnable = Runnable("tap", "/bin/sh", tap_path)
        runner = runner_tap.TAPRunner()
        results = [status for status in runner.run(runnable)]
        last_result = results[-1]
        self.assertEqual(last_result["status"], "finished")
        self.assertEqual(last_result["result"], "fail")
        self.assertEqual(last_result["returncode"], 0)

    @skipUnlessPathExists("/bin/sh")
    def test_ok(self):
        tap_script = """#!/bin/sh
echo '1..2'
echo '# Defining a basic test'
echo 'ok 1 - description 1'
echo 'ok 2 - description 2'"""
        tap_path = os.path.join(self.tmpdir.name, "tap.sh")

        with open(tap_path, "w", encoding="utf-8") as fp:
            fp.write(tap_script)

        runnable = Runnable("tap", "/bin/sh", tap_path)
        runner = runner_tap.TAPRunner()
        results = [status for status in runner.run(runnable)]
        last_result = results[-1]
        self.assertEqual(last_result["status"], "finished")
        self.assertEqual(last_result["result"], "pass")
        self.assertEqual(last_result["returncode"], 0)

    @skipUnlessPathExists("/bin/sh")
    def test_skip(self):
        tap_script = """#!/bin/sh
echo '1..2'
echo '# Defining a basic test'
echo 'ok 1 - # SKIP description 1'
echo 'ok 2 - description 2'"""
        tap_path = os.path.join(self.tmpdir.name, "tap.sh")

        with open(tap_path, "w", encoding="utf-8") as fp:
            fp.write(tap_script)

        runnable = Runnable("tap", "/bin/sh", tap_path)
        runner = runner_tap.TAPRunner()
        results = [status for status in runner.run(runnable)]
        last_result = results[-1]
        self.assertEqual(last_result["status"], "finished")
        self.assertEqual(last_result["result"], "pass")
        self.assertEqual(last_result["returncode"], 0)

    @skipUnlessPathExists("/bin/sh")
    def test_bailout(self):
        tap_script = """#!/bin/sh
echo '1..2'
echo '# Defining a basic test'
echo 'Bail out! - description 1'
echo 'ok 2 - description 2'"""
        tap_path = os.path.join(self.tmpdir.name, "tap.sh")

        with open(tap_path, "w", encoding="utf-8") as fp:
            fp.write(tap_script)

        runnable = Runnable("tap", "/bin/sh", tap_path)
        runner = runner_tap.TAPRunner()
        results = [status for status in runner.run(runnable)]
        last_result = results[-1]
        self.assertEqual(last_result["status"], "finished")
        self.assertEqual(last_result["result"], "error")
        self.assertEqual(last_result["returncode"], 0)

    @skipUnlessPathExists("/bin/sh")
    def test_error(self):
        tap_script = """#!/bin/sh
echo '1..2'
echo '# Defining a basic test'
echo 'error - description 1'
echo 'ok 2 - description 2'"""
        tap_path = os.path.join(self.tmpdir.name, "tap.sh")

        with open(tap_path, "w", encoding="utf-8") as fp:
            fp.write(tap_script)

        runnable = Runnable("tap", "/bin/sh", tap_path)
        runner = runner_tap.TAPRunner()
        results = [status for status in runner.run(runnable)]
        last_result = results[-1]
        self.assertEqual(last_result["status"], "finished")
        self.assertEqual(last_result["result"], "error")
        self.assertEqual(last_result["returncode"], 0)

    def tearDown(self):
        self.tmpdir.cleanup()
