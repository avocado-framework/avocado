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
import unittest
import os
import shutil
import time
import sys
import tempfile
import xml.dom.minidom

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

VOID_PLUGIN_CONTENTS = """#!/usr/bin/env python
from avocado.plugins.plugin import Plugin
class VoidPlugin(Plugin):
    pass
"""

SYNTAX_ERROR_PLUGIN_CONTENTS = """#!/usr/bin/env python
from avocado.plugins.plugin import Plugin
class VoidPlugin(Plugin)
"""

HELLO_PLUGIN_CONTENTS = """#!/usr/bin/env python
from avocado.plugins.plugin import Plugin
class HelloWorld(Plugin):
    name = 'hello'
    enabled = True
    def configure(self, parser):
        self.parser = parser.subcommands.add_parser('hello')
        super(HelloWorld, self).configure(self.parser)
    def run(self, args):
        print 'Hello World!'
"""


class RunnerOperationTest(unittest.TestCase):

    def test_runner_all_ok(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run sleeptest sleeptest'
        process.run(cmd_line)

    def test_datadir_alias(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run datadir'
        process.run(cmd_line)

    def test_datadir_noalias(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run tests/datadir.py tests/datadir.py'
        process.run(cmd_line)

    def test_runner_noalias(self):
        os.chdir(basedir)
        cmd_line = "./scripts/avocado run tests/sleeptest.py tests/sleeptest.py"
        process.run(cmd_line)

    def test_runner_tests_fail(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run sleeptest failtest sleeptest'
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

    def test_runner_doublefail(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado --xunit - run doublefail'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = 1
        unexpected_rc = 3
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))
        self.assertIn("TestError: Failing during cleanup. Yay!", output,
                      "Cleanup exception not printed to log output")
        self.assertIn("TestFail: This test is supposed to fail",
                      output,
                      "Test did not fail with action exception:\n%s" % output)

    def test_runner_timeout(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado --xunit - run timeouttest'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = 1
        unexpected_rc = 3
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))
        self.assertIn("TestTimeoutError: Timeout reached waiting for", output,
                      "Test did not fail with timeout exception:\n%s" % output)
        # Ensure no test aborted error messages show up
        self.assertNotIn("TestAbortedError: Test aborted unexpectedly", output)

    def test_runner_abort(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado --xunit - run abort'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 1
        unexpected_rc = 3
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def test_silent_output(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run sleeptest --silent'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        expected_output = ''
        self.assertEqual(result.exit_status, expected_rc)
        self.assertEqual(result.stderr, expected_output)

    def test_empty_args_list(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        unexpected_output = 'too few arguments'
        self.assertEqual(result.exit_status, expected_rc)
        self.assertNotIn(unexpected_output, result.stdout)

    def test_empty_test_list(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 2
        expected_output = 'Empty test ID. A test path or alias must be provided'
        expected_output_2 = 'usage:'
        self.assertEqual(result.exit_status, expected_rc)
        self.assertIn(expected_output, result.stderr)
        self.assertIn(expected_output_2, result.stdout)

    def test_not_found(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run sbrubles'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 1
        self.assertEqual(result.exit_status, expected_rc)
        self.assertIn('NOT_FOUND', result.stderr)
        self.assertIn('NOT FOUND : 1', result.stderr)


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

    def test_runner_onehundred_fail_timing(self):
        """
        We can be pretty sure that a failtest should return immediattely. Let's
        run 100 of them and assure they not take more than 30 seconds to run.

        Notice: on a current machine this takes about 0.12s, so 30 seconds is
        considered to be pretty safe here.
        """
        os.chdir(basedir)
        one_hundred = 'failtest ' * 100
        cmd_line = './scripts/avocado run %s' % one_hundred
        initial_time = time.time()
        result = process.run(cmd_line, ignore_status=True)
        actual_time = time.time() - initial_time
        self.assertLess(actual_time, 30.0)
        expected_rc = 1
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def test_runner_sleep_fail_sleep_timing(self):
        """
        Sleeptest is supposed to take 1 second, let's make a sandwich of
        100 failtests and check the test runner timing.
        """
        os.chdir(basedir)
        sleep_fail_sleep = 'sleeptest ' + 'failtest ' * 100 + 'sleeptest'
        cmd_line = './scripts/avocado run %s' % sleep_fail_sleep
        initial_time = time.time()
        result = process.run(cmd_line, ignore_status=True)
        actual_time = time.time() - initial_time
        self.assertLess(actual_time, 33.0)
        expected_rc = 1
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def tearDown(self):
        if os.path.isdir(self.base_logdir):
            shutil.rmtree(self.base_logdir, ignore_errors=True)


class ExternalPluginsTest(unittest.TestCase):

    def setUp(self):
        self.base_sourcedir = tempfile.mkdtemp(prefix='avocado_source_plugins')

    def test_void_plugin(self):
        self.void_plugin = os.path.join(self.base_sourcedir, 'avocado_void.py')
        with open(self.void_plugin, 'w') as void:
            void.write(VOID_PLUGIN_CONTENTS)
            os.chmod(self.void_plugin, 0775)
        os.chdir(basedir)
        cmd_line = './scripts/avocado --plugins %s plugins' % self.base_sourcedir
        result = process.run(cmd_line, ignore_status=True)
        expected_output = 'noname'
        self.assertIn(expected_output, result.stdout)

    def test_syntax_error_plugin(self):
        self.syntax_err_plugin = os.path.join(self.base_sourcedir, 'avocado_syntax_err.py')
        with open(self.syntax_err_plugin, 'w') as synerr:
            synerr.write(SYNTAX_ERROR_PLUGIN_CONTENTS)
            os.chmod(self.syntax_err_plugin, 0775)

        os.chdir(basedir)
        cmd_line = './scripts/avocado --plugins %s' % self.base_sourcedir
        result = process.run(cmd_line, ignore_status=True)
        expected_output = 'invalid syntax'
        self.assertIn(expected_output, result.stderr)

    def test_hello_plugin(self):
        self.hello_plugin = os.path.join(self.base_sourcedir, 'avocado_hello.py')
        with open(self.hello_plugin, 'w') as hello:
            hello.write(HELLO_PLUGIN_CONTENTS)
            os.chmod(self.hello_plugin, 0775)
        os.chdir(basedir)
        cmd_line = './scripts/avocado --plugins %s hello' % self.base_sourcedir
        result = process.run(cmd_line, ignore_status=True)
        expected_output = 'Hello World!'
        self.assertIn(expected_output, result.stdout)

    def tearDown(self):
        if os.path.isdir(self.base_sourcedir):
            shutil.rmtree(self.base_sourcedir, ignore_errors=True)


class PluginsTest(unittest.TestCase):

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

    def test_list_plugin(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado list'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn('No tests were found on current tests dir', output)

    def test_plugin_list(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado plugins'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn('Disabled', output)

    def test_datadir_plugin(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado datadir'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn('Disabled', output)


class ParseXMLError(Exception):
    pass


class PluginsXunitTest(PluginsTest):

    def run_and_check(self, testname, e_rc, e_ntests, e_nerrors,
                      e_nnotfound, e_nfailures, e_nskip):
        os.chdir(basedir)
        cmd_line = './scripts/avocado --xunit - run %s' % testname
        result = process.run(cmd_line, ignore_status=True)
        xml_output = result.stdout
        self.assertEqual(result.exit_status, e_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (e_rc, result))
        try:
            xunit_doc = xml.dom.minidom.parseString(xml_output)
        except Exception, detail:
            raise ParseXMLError("Failed to parse content: %s\n%s" %
                                (detail, xml_output))

        testsuite_list = xunit_doc.getElementsByTagName('testsuite')
        self.assertEqual(len(testsuite_list), 1, 'More than one testsuite tag')

        testsuite_tag = testsuite_list[0]
        self.assertEqual(len(testsuite_tag.attributes), 8,
                         'The testsuite tag does not have 8 attributes. '
                         'XML:\n%s' % xml_output)

        n_tests = int(testsuite_tag.attributes['tests'].value)
        self.assertEqual(n_tests, e_ntests,
                         "Unexpected number of executed tests, "
                         "XML:\n%s" % xml_output)

        n_errors = int(testsuite_tag.attributes['errors'].value)
        self.assertEqual(n_errors, e_nerrors,
                         "Unexpected number of test errors, "
                         "XML:\n%s" % xml_output)

        n_not_found = int(testsuite_tag.attributes['not_found'].value)
        self.assertEqual(n_not_found, e_nnotfound,
                         "Unexpected number of test not found, "
                         "XML:\n%s" % xml_output)

        n_failures = int(testsuite_tag.attributes['failures'].value)
        self.assertEqual(n_failures, e_nfailures,
                         "Unexpected number of test failures, "
                         "XML:\n%s" % xml_output)

        n_skip = int(testsuite_tag.attributes['skip'].value)
        self.assertEqual(n_skip, e_nskip,
                         "Unexpected number of test skips, "
                         "XML:\n%s" % xml_output)

    def test_xunit_plugin_sleeptest(self):
        self.run_and_check('sleeptest', 0, 1, 0, 0, 0, 0)

    def test_xunit_plugin_failtest(self):
        self.run_and_check('failtest', 1, 1, 0, 0, 1, 0)

    def test_xunit_plugin_skiptest(self):
        self.run_and_check('skiptest', 0, 1, 0, 0, 0, 1)

    def test_xunit_plugin_errortest(self):
        self.run_and_check('errortest', 1, 1, 1, 0, 0, 0)

    def test_xunit_plugin_notfoundtest(self):
        self.run_and_check('sbrubles', 1, 1, 0, 1, 0, 0)

    def test_xunit_plugin_mixedtest(self):
        self.run_and_check('sleeptest failtest skiptest errortest sbrubles',
                           1, 5, 1, 1, 1, 1)


class ParseJSONError(Exception):
    pass


class PluginsJSONTest(PluginsTest):

    def run_and_check(self, testname, e_rc, e_ntests, e_nerrors, e_nnotfound,
                      e_nfailures, e_nskip):
        os.chdir(basedir)
        cmd_line = './scripts/avocado --json - run --archive %s' % testname
        result = process.run(cmd_line, ignore_status=True)
        json_output = result.stdout
        self.assertEqual(result.exit_status, e_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (e_rc, result))
        try:
            json_data = json.loads(json_output)
        except Exception, detail:
            raise ParseJSONError("Failed to parse content: %s\n%s" %
                                 (detail, json_output))
        self.assertTrue(json_data, "Empty JSON result:\n%s" % json_output)
        self.assertIsInstance(json_data['tests'], list,
                              "JSON result lacks 'tests' list")
        n_tests = len(json_data['tests'])
        self.assertEqual(n_tests, e_ntests,
                         "Different number of expected tests")
        n_errors = json_data['errors']
        self.assertEqual(n_errors, e_nerrors,
                         "Different number of expected tests")
        n_not_found = json_data['not_found']
        self.assertEqual(n_not_found, e_nnotfound,
                         "Different number of not found tests")
        n_failures = json_data['failures']
        self.assertEqual(n_failures, e_nfailures,
                         "Different number of expected tests")
        n_skip = json_data['skip']
        self.assertEqual(n_skip, e_nskip,
                         "Different number of skipped tests")

    def test_json_plugin_sleeptest(self):
        self.run_and_check('sleeptest', 0, 1, 0, 0, 0, 0)

    def test_json_plugin_failtest(self):
        self.run_and_check('failtest', 1, 1, 0, 0, 1, 0)

    def test_json_plugin_skiptest(self):
        self.run_and_check('skiptest', 0, 1, 0, 0, 0, 1)

    def test_json_plugin_errortest(self):
        self.run_and_check('errortest', 1, 1, 1, 0, 0, 0)

    def test_json_plugin_notfoundtest(self):
        self.run_and_check('sbrubles', 1, 1, 0, 1, 0, 0)

    def test_json_plugin_mixedtest(self):
        self.run_and_check('sleeptest failtest skiptest errortest sbrubles',
                           1, 5, 1, 1, 1, 1)

if __name__ == '__main__':
    unittest.main()
