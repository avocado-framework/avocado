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

import json
import tempfile
import unittest
import os
import sys
from xml.dom import minidom

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import process


class OutputTest(unittest.TestCase):

    def test_output_doublefree(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run doublefree'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 1
        output = result.stdout + result.stderr
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        bad_string = 'double free or corruption'
        self.assertNotIn(bad_string, output,
                         "Libc double free can be seen in avocado "
                         "doublefree output:\n%s" % output)


class OutputPluginTest(unittest.TestCase):

    def check_output_files(self, debug_log):
        base_dir = os.path.dirname(debug_log)
        json_output = os.path.join(base_dir, 'results.json')
        self.assertTrue(os.path.isfile(json_output))
        with open(json_output, 'r') as fp:
            json.load(fp)
        xunit_output = os.path.join(base_dir, 'results.xml')
        self.assertTrue(os.path.isfile(json_output))
        minidom.parse(xunit_output)

    def test_output_incompatible_setup(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado --xunit - --json - run sleeptest'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 2
        output = result.stdout + result.stderr
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        error_excerpt = "Avocado could not set --json and --xunit both to output to stdout."
        self.assertIn(error_excerpt, output,
                      "Missing excepted error message from output:\n%s" % output)

    def test_output_incompatible_setup_2(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado --vm --json - run sleeptest'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 2
        output = result.stdout + result.stderr
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        error_excerpt = "Avocado could not set --json and --vm both to output to stdout."
        self.assertIn(error_excerpt, output,
                      "Missing excepted error message from output:\n%s" % output)

    def test_output_compatible_setup(self):
        tmpfile = tempfile.mktemp()
        os.chdir(basedir)
        cmd_line = './scripts/avocado --journal --xunit %s --json - run sleeptest' % tmpfile
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = 0
        try:
            self.assertEqual(result.exit_status, expected_rc,
                             "Avocado did not return rc %d:\n%s" %
                             (expected_rc, result))
            # Check if we are producing valid outputs
            json.loads(output)
            minidom.parse(tmpfile)
        finally:
            try:
                os.remove(tmpfile)
            except OSError:
                pass

    def test_output_compatible_setup_2(self):
        tmpfile = tempfile.mktemp()
        os.chdir(basedir)
        cmd_line = './scripts/avocado --xunit - --json %s run sleeptest' % tmpfile
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = 0
        try:
            self.assertEqual(result.exit_status, expected_rc,
                             "Avocado did not return rc %d:\n%s" %
                             (expected_rc, result))
            # Check if we are producing valid outputs
            with open(tmpfile, 'r') as fp:
                json_results = json.load(fp)
                debug_log = json_results['debuglog']
                self.check_output_files(debug_log)
            minidom.parseString(output)
        finally:
            try:
                os.remove(tmpfile)
            except OSError:
                pass

    def test_output_compatible_setup_nooutput(self):
        tmpfile = tempfile.mktemp()
        tmpfile2 = tempfile.mktemp()
        os.chdir(basedir)
        cmd_line = './scripts/avocado --xunit %s --json %s run sleeptest' % (tmpfile, tmpfile2)
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = 0
        try:
            self.assertEqual(result.exit_status, expected_rc,
                             "Avocado did not return rc %d:\n%s" %
                             (expected_rc, result))
            self.assertEqual(output, "",
                             "Output is not empty as expected:\n%s" % output)
            # Check if we are producing valid outputs
            with open(tmpfile2, 'r') as fp:
                json_results = json.load(fp)
                debug_log = json_results['debuglog']
                self.check_output_files(debug_log)
            minidom.parse(tmpfile)
        finally:
            try:
                os.remove(tmpfile)
                os.remove(tmpfile2)
            except OSError:
                pass

    def test_default_enabled_plugins(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run sleeptest'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        output_lines = output.splitlines()
        first_line = output_lines[0]
        debug_log = first_line.split()[-1]
        self.check_output_files(debug_log)


if __name__ == '__main__':
    unittest.main()
