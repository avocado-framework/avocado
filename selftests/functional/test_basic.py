import json
import os
import shutil
import time
import sys
import tempfile
import xml.dom.minidom
import glob
import aexpect
import signal
import re

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import exit_codes
from avocado.utils import astring
from avocado.utils import process
from avocado.utils import script


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


PASS_SCRIPT_CONTENTS = """#!/bin/sh
true
"""

PASS_SHELL_CONTENTS = "exit 0"

FAIL_SCRIPT_CONTENTS = """#!/bin/sh
false
"""

FAIL_SHELL_CONTENTS = "exit 1"

HELLO_LIB_CONTENTS = """
def hello():
    return 'Hello world'
"""

LOCAL_IMPORT_TEST_CONTENTS = '''
from avocado import Test
from mylib import hello

class LocalImportTest(Test):
    def test(self):
        self.log.info(hello())
'''

UNSUPPORTED_STATUS_TEST_CONTENTS = '''
from avocado import Test

class FakeStatusTest(Test):
    def run_avocado(self):
        super(FakeStatusTest, self).run_avocado()
        self.status = 'not supported'

    def test(self):
        pass
'''

INVALID_PYTHON_TEST = '''
from avocado import Test

class MyTest(Test):

    non_existing_variable_causing_crash

    def test_my_name(self):
        pass
'''


class RunnerOperationTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def test_show_version(self):
        result = process.run('./scripts/avocado -v', ignore_status=True)
        self.assertEqual(result.exit_status, 0)
        version_re = r"^Avocado \d+\.\d+(lts)?$"
        self.assertTrue(re.match(version_re, result.stderr),
                        "Version string does not match '%r\n"
                        "%s" % (version_re, result.stderr))

    def test_alternate_config_datadir(self):
        """
        Uses the "--config" flag to check custom configuration is applied

        Even on the more complex data_dir module, which adds extra checks
        to what is set on the plain settings module.
        """
        base_dir = os.path.join(self.tmpdir, 'datadir_base')
        os.mkdir(base_dir)
        mapping = {'base_dir': base_dir,
                   'test_dir': os.path.join(base_dir, 'test'),
                   'data_dir': os.path.join(base_dir, 'data'),
                   'logs_dir': os.path.join(base_dir, 'logs')}
        config = '[datadir.paths]'
        for key, value in mapping.iteritems():
            if not os.path.isdir(value):
                os.mkdir(value)
            config += "%s = %s\n" % (key, value)
        fd, config_file = tempfile.mkstemp(dir=self.tmpdir)
        os.write(fd, config)
        os.close(fd)

        os.chdir(basedir)
        cmd = './scripts/avocado --config %s config --datadir' % config_file
        result = process.run(cmd)
        output = result.stdout
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn('    base     ' + mapping['base_dir'], result.stdout)
        self.assertIn('    data     ' + mapping['data_dir'], result.stdout)
        self.assertIn('    logs     ' + mapping['logs_dir'], result.stdout)

    def test_runner_all_ok(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    'passtest.py passtest.py' % self.tmpdir)
        process.run(cmd_line)

    def test_datadir_alias(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    'datadir.py' % self.tmpdir)
        process.run(cmd_line)

    def test_shell_alias(self):
        """ Tests that .sh files are also executable via alias """
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    'env_variables.sh' % self.tmpdir)
        process.run(cmd_line)

    def test_datadir_noalias(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s examples/tests/datadir.py '
                    'examples/tests/datadir.py' % self.tmpdir)
        process.run(cmd_line)

    def test_runner_noalias(self):
        os.chdir(basedir)
        cmd_line = ("./scripts/avocado run --sysinfo=off --job-results-dir %s examples/tests/passtest.py "
                    "examples/tests/passtest.py" % self.tmpdir)
        process.run(cmd_line)

    def test_runner_test_with_local_imports(self):
        mylib = script.TemporaryScript(
            'mylib.py',
            HELLO_LIB_CONTENTS,
            'avocado_simpletest_functional')
        mylib.save()
        mytest = script.Script(
            os.path.join(os.path.dirname(mylib.path), 'test_local_imports.py'),
            LOCAL_IMPORT_TEST_CONTENTS)
        os.chdir(basedir)
        mytest.save()
        cmd_line = ("./scripts/avocado run --sysinfo=off --job-results-dir %s "
                    "%s" % (self.tmpdir, mytest))
        process.run(cmd_line)

    def test_unsupported_status(self):
        os.chdir(basedir)
        with script.TemporaryScript("fake_status.py",
                                    UNSUPPORTED_STATUS_TEST_CONTENTS,
                                    "avocado_unsupported_status") as tst:
            res = process.run("./scripts/avocado run --sysinfo=off "
                              "--job-results-dir %s %s --json -"
                              % (self.tmpdir, tst), ignore_status=True)
            self.assertEqual(res.exit_status, exit_codes.AVOCADO_TESTS_FAIL)
            results = json.loads(res.stdout)
            self.assertEqual(results["tests"][0]["status"], "ERROR",
                             "%s != %s\n%s" % (results["tests"][0]["status"],
                                               "ERROR", res))
            self.assertIn("Original fail_reason: None",
                          results["tests"][0]["fail_reason"])

    def test_runner_tests_fail(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    'passtest.py failtest.py passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def test_runner_nonexistent_test(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir '
                    '%s bogustest' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        unexpected_rc = exit_codes.AVOCADO_FAIL
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def test_runner_doublefail(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    '--xunit - doublefail.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        unexpected_rc = exit_codes.AVOCADO_FAIL
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))
        self.assertIn("TestError: Failing during tearDown. Yay!", output,
                      "Cleanup exception not printed to log output")
        self.assertIn("TestFail: This test is supposed to fail",
                      output,
                      "Test did not fail with action exception:\n%s" % output)

    def test_uncaught_exception(self):
        os.chdir(basedir)
        cmd_line = ("./scripts/avocado run --sysinfo=off --job-results-dir %s "
                    "--json - uncaught_exception.py" % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc,
                                                                result))
        self.assertIn('"status": "ERROR"', result.stdout)

    def test_fail_on_exception(self):
        os.chdir(basedir)
        cmd_line = ("./scripts/avocado run --sysinfo=off --job-results-dir %s "
                    "--json - fail_on_exception.py" % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc,
                                                                result))
        self.assertIn('"status": "FAIL"', result.stdout)

    def test_runner_timeout(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    '--xunit - timeouttest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = exit_codes.AVOCADO_JOB_INTERRUPTED
        unexpected_rc = exit_codes.AVOCADO_FAIL
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))
        self.assertIn("RUNNER: Timeout reached", output,
                      "Timeout reached message not found in the output:\n%s" % output)
        # Ensure no test aborted error messages show up
        self.assertNotIn("TestAbortedError: Test aborted unexpectedly", output)

    def test_runner_abort(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    '--xunit - abort.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        excerpt = 'Test process aborted'
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        unexpected_rc = exit_codes.AVOCADO_FAIL
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))
        self.assertIn(excerpt, output)

    def test_silent_output(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado --silent run --sysinfo=off '
                    '--job-results-dir %s passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        expected_output = ''
        self.assertEqual(result.exit_status, expected_rc)
        self.assertEqual(result.stdout, expected_output)

    def test_empty_args_list(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_FAIL
        expected_output = 'error: too few arguments'
        self.assertEqual(result.exit_status, expected_rc)
        self.assertIn(expected_output, result.stderr)

    def test_empty_test_list(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        expected_output = 'No urls provided nor any arguments produced'
        self.assertEqual(result.exit_status, expected_rc)
        self.assertIn(expected_output, result.stderr)

    def test_not_found(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off sbrubles'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        self.assertEqual(result.exit_status, expected_rc)
        self.assertIn('Unable to discover url', result.stderr)
        self.assertNotIn('Unable to discover url', result.stdout)

    def test_invalid_unique_id(self):
        cmd_line = ('./scripts/avocado run --sysinfo=off --force-job-id foobar'
                    ' passtest.py')
        result = process.run(cmd_line, ignore_status=True)
        self.assertNotEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertIn('needs to be a 40 digit hex', result.stderr)
        self.assertNotIn('needs to be a 40 digit hex', result.stdout)

    def test_valid_unique_id(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--force-job-id 975de258ac05ce5e490648dec4753657b7ccc7d1 '
                    'passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertNotIn('needs to be a 40 digit hex', result.stderr)
        self.assertIn('PASS', result.stdout)

    def test_automatic_unique_id(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    'passtest.py --json -' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        r = json.loads(result.stdout)
        int(r['job_id'], 16)  # it's an hex number
        self.assertEqual(len(r['job_id']), 40)

    def test_skip_outside_setup(self):
        os.chdir(basedir)
        cmd_line = ("./scripts/avocado run --sysinfo=off --job-results-dir %s "
                    "--json - skip_outside_setup.py" % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc,
                                                                result))
        self.assertIn('"status": "ERROR"', result.stdout)

    def test_early_latest_result(self):
        """
        Tests that the `latest` link to the latest job results is created early
        """
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    'examples/tests/passtest.py' % self.tmpdir)
        avocado_process = process.SubProcess(cmd_line)
        avocado_process.start()
        link = os.path.join(self.tmpdir, 'latest')
        for trial in xrange(0, 50):
            time.sleep(0.1)
            if os.path.exists(link) and os.path.islink(link):
                avocado_process.wait()
                break
        self.assertTrue(os.path.exists(link))
        self.assertTrue(os.path.islink(link))

    def test_dry_run(self):
        os.chdir(basedir)
        cmd = ("./scripts/avocado run --sysinfo=off passtest.py failtest.py "
               "errortest.py --json - --mux-inject foo:1 bar:2 baz:3 foo:foo:a"
               " foo:bar:b foo:baz:c bar:bar:bar --dry-run")
        result = json.loads(process.run(cmd).stdout)
        debuglog = result['debuglog']
        log = open(debuglog, 'r').read()
        # Remove the result dir
        shutil.rmtree(os.path.dirname(os.path.dirname(debuglog)))
        self.assertIn('/tmp', debuglog)   # Use tmp dir, not default location
        self.assertEqual(result['job_id'], u'0' * 40)
        # Check if all tests were skipped
        self.assertEqual(result['skip'], 3)
        for i in xrange(3):
            test = result['tests'][i]
            self.assertEqual(test['fail_reason'],
                             u'Test skipped due to --dry-run')
        # Check if all params are listed
        # The "/:bar ==> 2 is in the tree, but not in any leave so inaccessible
        # from test.
        for line in ("/:foo ==> 1", "/:baz ==> 3", "/foo:foo ==> a",
                     "/foo:bar ==> b", "/foo:baz ==> c", "/bar:bar ==> bar"):
            self.assertEqual(log.count(line), 3)

    def test_invalid_python(self):
        os.chdir(basedir)
        test = script.make_script(os.path.join(self.tmpdir, 'test.py'),
                                  INVALID_PYTHON_TEST)
        cmd_line = './scripts/avocado --show test run --sysinfo=off '\
                   '--job-results-dir %s %s' % (self.tmpdir, test)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn('1-%s:MyTest.test_my_name -> TestError' % test,
                      result.stdout)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class RunnerHumanOutputTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def test_output_pass(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    'passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn('passtest.py:PassTest.test:  PASS', result.stdout)

    def test_output_fail(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    'failtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn('failtest.py:FailTest.test:  FAIL', result.stdout)

    def test_output_error(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    'errortest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn('errortest.py:ErrorTest.test:  ERROR', result.stdout)

    def test_output_skip(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    'skiponsetup.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn('skiponsetup.py:SkipOnSetupTest.test_wont_be_executed:'
                      '  SKIP', result.stdout)

    def test_ugly_echo_cmd(self):
        if not os.path.exists("/bin/echo"):
            self.skipTest("Program /bin/echo does not exist")
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run "/bin/echo -ne '
                    'foo\\\\\\n\\\'\\\\\\"\\\\\\nbar/baz" --job-results-dir %s'
                    ' --sysinfo=off  --show-job-log' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %s:\n%s" %
                         (expected_rc, result))
        self.assertIn('[stdout] foo', result.stdout, result)
        self.assertIn('[stdout] \'"', result.stdout, result)
        self.assertIn('[stdout] bar/baz', result.stdout, result)
        self.assertIn('PASS 1-/bin/echo -ne foo\\\\n\\\'\\"\\\\nbar/baz',
                      result.stdout, result)
        # logdir name should escape special chars (/)
        test_dirs = glob.glob(os.path.join(self.tmpdir, 'latest',
                                           'test-results', '*'))
        self.assertEqual(len(test_dirs), 1, "There are multiple directories in"
                         " test-results dir, but only one test was executed: "
                         "%s" % (test_dirs))
        self.assertEqual(os.path.basename(test_dirs[0]),
                         '1-_bin_echo -ne foo\\\\n\\\'\\"\\\\nbar_baz')

    def test_replay_skip_skipped(self):
        result = process.run("./scripts/avocado run skiponsetup.py --json -")
        result = json.loads(result.stdout)
        jobid = result["job_id"]
        process.run(str("./scripts/avocado run --replay %s "
                        "--replay-test-status PASS" % jobid))

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class RunnerSimpleTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.pass_script = script.TemporaryScript(
            'avocado_pass.sh',
            PASS_SCRIPT_CONTENTS,
            'avocado_simpletest_functional')
        self.pass_script.save()
        self.fail_script = script.TemporaryScript('avocado_fail.sh',
                                                  FAIL_SCRIPT_CONTENTS,
                                                  'avocado_simpletest_'
                                                  'functional')
        self.fail_script.save()

    def test_simpletest_pass(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off'
                    ' %s' % (self.tmpdir, self.pass_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def test_simpletest_fail(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off'
                    ' %s' % (self.tmpdir, self.fail_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
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
        one_hundred = 'failtest.py ' * 100
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off'
                    ' %s' % (self.tmpdir, one_hundred))
        initial_time = time.time()
        result = process.run(cmd_line, ignore_status=True)
        actual_time = time.time() - initial_time
        self.assertLess(actual_time, 30.0)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def test_runner_sleep_fail_sleep_timing(self):
        """
        Sleeptest is supposed to take 1 second, let's make a sandwich of
        100 failtests and check the test runner timing.
        """
        os.chdir(basedir)
        sleep_fail_sleep = ('sleeptest.py ' + 'failtest.py ' * 100 +
                            'sleeptest.py')
        cmd_line = './scripts/avocado run --job-results-dir %s --sysinfo=off %s' % (
            self.tmpdir, sleep_fail_sleep)
        initial_time = time.time()
        result = process.run(cmd_line, ignore_status=True)
        actual_time = time.time() - initial_time
        self.assertLess(actual_time, 33.0)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def test_simplewarning(self):
        """
        simplewarning.sh uses the avocado-bash-utils
        """
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    'examples/tests/simplewarning.sh --show-job-log' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %s:\n%s" %
                         (expected_rc, result))
        self.assertIn('DEBUG| Debug message', result.stdout, result)
        self.assertIn('INFO | Info message', result.stdout, result)
        self.assertIn('WARN | Warning message (should cause this test to '
                      'finish with warning)', result.stdout, result)
        self.assertIn('ERROR| Error message (ordinary message not changing '
                      'the results)', result.stdout, result)

    def test_non_absolute_path(self):
        avocado_path = os.path.join(basedir, 'scripts', 'avocado')
        test_base_dir = os.path.dirname(self.pass_script.path)
        test_file_name = os.path.basename(self.pass_script.path)
        os.chdir(test_base_dir)
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off'
                    ' %s' % (avocado_path, self.tmpdir, test_file_name))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def test_kill_stopped_sleep(self):
        sleep = process.run("which sleep", ignore_status=True, shell=True)
        if sleep.exit_status:
            self.skipTest("Sleep binary not found in PATH")
        sleep = "'%s 60'" % sleep.stdout.strip()
        proc = aexpect.Expect("./scripts/avocado run %s --job-results-dir %s "
                              "--sysinfo=off --job-timeout 3"
                              % (sleep, self.tmpdir))
        proc.read_until_output_matches(["\(1/1\)"], timeout=3,
                                       internal_timeout=0.01)
        # We need pid of the avocado, not the shell executing it
        pid = int(process.get_children_pids(proc.get_pid())[0])
        os.kill(pid, signal.SIGTSTP)   # This freezes the process
        deadline = time.time() + 9
        while time.time() < deadline:
            if not proc.is_alive():
                break
            time.sleep(0.1)
        else:
            proc.kill(signal.SIGKILL)
            self.fail("Avocado process still alive 5s after job-timeout:\n%s"
                      % proc.get_output())
        output = proc.get_output()
        self.assertIn("ctrl+z pressed, stopping test", output, "SIGTSTP "
                      "message not in the output, test was probably not "
                      "stopped.")
        self.assertIn("TIME", output, "TIME not in the output, avocado "
                      "probably died unexpectadly")
        self.assertEqual(proc.get_status(), 8, "Avocado did not finish with "
                         "1.")
        sleep_dir = astring.string_to_safe_path("1-" + sleep[1:-1])
        debug_log = os.path.join(self.tmpdir, "latest", "test-results",
                                 sleep_dir, "debug.log")
        debug_log = open(debug_log).read()
        self.assertIn("RUNNER: Timeout reached", debug_log, "RUNNER: Timeout "
                      "reached message not in the test's debug.log:\n%s"
                      % debug_log)
        self.assertNotIn("Traceback", debug_log, "Traceback present in the "
                         "test's debug.log file, but it was suppose to be "
                         "stopped and unable to produce it.\n%s" % debug_log)

    def tearDown(self):
        self.pass_script.remove()
        self.fail_script.remove()
        shutil.rmtree(self.tmpdir)


class ExternalRunnerTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.pass_script = script.TemporaryScript(
            'pass',
            PASS_SHELL_CONTENTS,
            'avocado_externalrunner_functional')
        self.pass_script.save()
        self.fail_script = script.TemporaryScript(
            'fail',
            FAIL_SHELL_CONTENTS,
            'avocado_externalrunner_functional')
        self.fail_script.save()

    def test_externalrunner_pass(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --job-results-dir %s --sysinfo=off --external-runner=/bin/sh %s'
        cmd_line %= (self.tmpdir, self.pass_script.path)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def test_externalrunner_fail(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --job-results-dir %s --sysinfo=off --external-runner=/bin/sh %s'
        cmd_line %= (self.tmpdir, self.fail_script.path)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def test_externalrunner_chdir_no_testdir(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off --external-runner=/bin/sh '
                    '--external-runner-chdir=test %s')
        cmd_line %= (self.tmpdir, self.pass_script.path)
        result = process.run(cmd_line, ignore_status=True)
        expected_output = ('Option "--external-runner-chdir=test" requires '
                           '"--external-runner-testdir" to be set')
        self.assertIn(expected_output, result.stderr)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def test_externalrunner_no_url(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--external-runner=/bin/true' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_output = ('No urls provided nor any arguments produced')
        self.assertIn(expected_output, result.stderr)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def tearDown(self):
        self.pass_script.remove()
        self.fail_script.remove()
        shutil.rmtree(self.tmpdir)


class AbsPluginsTest(object):

    def setUp(self):
        self.base_outputdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def tearDown(self):
        shutil.rmtree(self.base_outputdir)


class PluginsTest(AbsPluginsTest, unittest.TestCase):

    def test_sysinfo_plugin(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado sysinfo %s' % self.base_outputdir
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
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
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn('No tests were found on current tests dir', output)

    def test_list_error_output(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado list sbrubles'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stderr
        expected_rc = exit_codes.AVOCADO_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn("Unable to discover url", output)

    def test_plugin_list(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado plugins'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        if sys.version_info[:2] >= (2, 7, 0):
            self.assertNotIn('Disabled', output)

    def test_config_plugin(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado config --paginator off'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn('Disabled', output)

    def test_config_plugin_datadir(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado config --datadir --paginator off'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn('Disabled', output)

    def test_Namespace_object_has_no_attribute(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado plugins'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stderr
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn("'Namespace' object has no attribute", output)


class ParseXMLError(Exception):
    pass


class PluginsXunitTest(AbsPluginsTest, unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        super(PluginsXunitTest, self).setUp()

    def run_and_check(self, testname, e_rc, e_ntests, e_nerrors,
                      e_nnotfound, e_nfailures, e_nskip):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off'
                    ' --xunit - %s' % (self.tmpdir, testname))
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

    def test_xunit_plugin_passtest(self):
        self.run_and_check('passtest.py', exit_codes.AVOCADO_ALL_OK,
                           1, 0, 0, 0, 0)

    def test_xunit_plugin_failtest(self):
        self.run_and_check('failtest.py', exit_codes.AVOCADO_TESTS_FAIL,
                           1, 0, 0, 1, 0)

    def test_xunit_plugin_skiponsetuptest(self):
        self.run_and_check('skiponsetup.py', exit_codes.AVOCADO_ALL_OK,
                           1, 0, 0, 0, 1)

    def test_xunit_plugin_errortest(self):
        self.run_and_check('errortest.py', exit_codes.AVOCADO_TESTS_FAIL,
                           1, 1, 0, 0, 0)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        super(PluginsXunitTest, self).tearDown()


class ParseJSONError(Exception):
    pass


class PluginsJSONTest(AbsPluginsTest, unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        super(PluginsJSONTest, self).setUp()

    def run_and_check(self, testname, e_rc, e_ntests, e_nerrors,
                      e_nfailures, e_nskip):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off --json - --archive %s' %
                    (self.tmpdir, testname))
        result = process.run(cmd_line, ignore_status=True)
        json_output = result.stdout
        self.assertEqual(result.exit_status, e_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (e_rc, result))
        try:
            json_data = json.loads(json_output)
        except Exception as detail:
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
        n_failures = json_data['failures']
        self.assertEqual(n_failures, e_nfailures,
                         "Different number of expected tests")
        n_skip = json_data['skip']
        self.assertEqual(n_skip, e_nskip,
                         "Different number of skipped tests")
        return json_data

    def test_json_plugin_passtest(self):
        self.run_and_check('passtest.py', exit_codes.AVOCADO_ALL_OK,
                           1, 0, 0, 0)

    def test_json_plugin_failtest(self):
        self.run_and_check('failtest.py', exit_codes.AVOCADO_TESTS_FAIL,
                           1, 0, 1, 0)

    def test_json_plugin_skiponsetuptest(self):
        self.run_and_check('skiponsetup.py', exit_codes.AVOCADO_ALL_OK,
                           1, 0, 0, 1)

    def test_json_plugin_errortest(self):
        self.run_and_check('errortest.py', exit_codes.AVOCADO_TESTS_FAIL,
                           1, 1, 0, 0)

    def test_ugly_echo_cmd(self):
        if not os.path.exists("/bin/echo"):
            self.skipTest("Program /bin/echo does not exist")
        data = self.run_and_check('"/bin/echo -ne foo\\\\\\n\\\'\\\\\\"\\\\\\'
                                  'nbar/baz"', exit_codes.AVOCADO_ALL_OK, 1, 0,
                                  0, 0)
        # The executed test should be this
        self.assertEqual(data['tests'][0]['url'],
                         '1-/bin/echo -ne foo\\\\n\\\'\\"\\\\nbar/baz')
        # logdir name should escape special chars (/)
        self.assertEqual(os.path.basename(data['tests'][0]['logdir']),
                         '1-_bin_echo -ne foo\\\\n\\\'\\"\\\\nbar_baz')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        super(PluginsJSONTest, self).tearDown()

if __name__ == '__main__':
    unittest.main()
