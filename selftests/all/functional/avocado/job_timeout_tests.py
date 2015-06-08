import os
import sys
import unittest
import tempfile
import shutil

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                       '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import process
from avocado.utils import script

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
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(basedir)

    def test_sleep_longer_timeout(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--job-timeout=5 %s examples/tests/passtest.py' % (self.tmpdir, self.script.path))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, 0)
        self.assertIn('PASS       : 2', result.stdout)
        self.assertIn('ERROR      : 0', result.stdout)
        self.assertIn('SKIP       : 0', result.stdout)

    def test_sleep_short_timeout(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--job-timeout=1 %s examples/tests/passtest.py' % (self.tmpdir, self.script.path))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, 1)
        self.assertIn('PASS       : 0', result.stdout)
        self.assertIn('ERROR      : 1', result.stdout)
        self.assertIn('SKIP       : 1', result.stdout)

    def test_sleep_short_timeout_with_test_methods(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--job-timeout=1 %s' % (self.tmpdir, self.py.path))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, 1)
        self.assertIn('PASS       : 0', result.stdout)
        self.assertIn('ERROR      : 1', result.stdout)
        self.assertIn('SKIP       : 2', result.stdout)

    def test_invalid_values(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--job-timeout=0 examples/tests/passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, 3)
        self.assertIn('Invalid number', result.stderr)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--job-timeout=123x examples/tests/passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, 3)
        self.assertIn('Invalid number', result.stderr)

    def test_valid_values(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--job-timeout=123 examples/tests/passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, 0)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--job-timeout=123s examples/tests/passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, 0)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--job-timeout=123m examples/tests/passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, 0)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--job-timeout=123h examples/tests/passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, 0)

    def tearDown(self):
        self.script.remove()
        self.py.remove()
        shutil.rmtree(self.tmpdir)

if __name__ == '__main__':
    unittest.main()
