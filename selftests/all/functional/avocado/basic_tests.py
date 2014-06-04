#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

import unittest
import os
import shutil
import sys
import tempfile

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import process

PASS_SCRIPT_CONTENTS = """#!/bin/sh
true
"""

FAIL_SCRIPT_CONTENTS = """#!/bin/sh
false
"""


class RunnerOperationTest(unittest.TestCase):

    def test_runner_all_ok(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run "sleeptest sleeptest"'
        process.run(cmd_line)

    def test_runner_tests_fail(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run "sleeptest failtest sleeptest"'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 1
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def test_runner_nonexistent_test(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run bogustest'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 1
        unexpected_rc = 3
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))


class RunnerDropinTest(unittest.TestCase):

    def setUp(self):
        self.base_logdir = tempfile.mkdtemp(prefix='avocado_dropin_functional')
        self.pass_script = os.path.join(self.base_logdir, 'avocado_pass.sh')
        with open(self.pass_script, 'w') as pass_script_obj:
            pass_script_obj.write(PASS_SCRIPT_CONTENTS)
        os.chmod(self.pass_script, 0775)

        self.fail_script = os.path.join(self.base_logdir, 'avocado_fail.sh')
        with open(self.fail_script, 'w') as fail_script_obj:
            fail_script_obj.write(FAIL_SCRIPT_CONTENTS)
        os.chmod(self.fail_script, 0775)

    def test_dropin_pass(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run %s' % self.pass_script
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def test_dropin_fail(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run %s' % self.fail_script
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 1
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def tearDown(self):
        if os.path.isdir(self.base_logdir):
            shutil.rmtree(self.base_logdir, ignore_errors=True)


class PluginsOperationTest(unittest.TestCase):

    def setUp(self):
        self.base_outputdir = tempfile.mkdtemp(prefix='avocado_plugins')

    def test_sysinfo_plugin(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado sysinfo %s' % self.base_outputdir
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        sysinfo_files = os.listdir(self.base_outputdir)
        self.assertGreater(len(sysinfo_files), 0, "Empty sysinfo files dir")

    def tearDown(self):
        if os.path.isdir(self.base_outputdir):
            shutil.rmtree(self.base_outputdir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
