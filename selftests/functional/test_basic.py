import glob
import json
import os
import re
import tempfile
import time
import unittest
import xml.dom.minidom
import zipfile

from avocado.core import exit_codes
from avocado.utils import path as utils_path
from avocado.utils import process, script
from selftests.utils import (AVOCADO, BASEDIR, TestCaseTmpDir,
                             python_module_available, skipOnLevelsInferiorThan,
                             skipUnlessPathExists, temp_dir_prefix)

try:
    import xmlschema
    SCHEMA_CAPABLE = True
except ImportError:
    SCHEMA_CAPABLE = False


UNSUPPORTED_STATUS_TEST_CONTENTS = '''
from avocado import Test

class FakeStatusTest(Test):
    def run_avocado(self):
        super(FakeStatusTest, self).run_avocado()
        # Please do NOT ever use this, it's for unittesting only.
        self._Test__status = 'not supported'

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


VALID_PYTHON_TEST_WITH_TAGS = '''
from avocado import Test

class MyTest(Test):
    def test(self):
         """
         :avocado: tags=BIG_TAG_NAME
         """
         pass
'''


REPORTS_STATUS_AND_HANG = '''
from avocado import Test
import time

class MyTest(Test):
    def test(self):
         self.runner_queue.put({"running": False})
         time.sleep(70)
'''


DIE_WITHOUT_REPORTING_STATUS = '''
from avocado import Test
import os
import signal

class MyTest(Test):
    def test(self):
         os.kill(os.getpid(), signal.SIGKILL)
'''


RAISE_CUSTOM_PATH_EXCEPTION_CONTENT = '''import os
import sys

from avocado import Test

class SharedLibTest(Test):
    def test(self):
        sys.path.append(os.path.join(os.path.dirname(__file__), "shared_lib"))
        from mylib import CancelExc
        raise CancelExc("This should not crash on unpickling in runner")
'''


TEST_OTHER_LOGGERS_CONTENT = '''
import logging
from avocado import Test

class My(Test):
    def test(self):
        logging.getLogger("some.other.logger").info("SHOULD NOT BE ON debug.log")
'''


def probe_binary(binary):
    try:
        return utils_path.find_command(binary)
    except utils_path.CmdNotFoundError:
        return None


TRUE_CMD = probe_binary('true')
CC_BINARY = probe_binary('cc')

# On macOS, the default GNU core-utils installation (brew)
# installs the gnu utility versions with a g prefix. It still has the
# BSD versions of the core utilities installed on their expected paths
# but their behavior and flags are in most cases different.
GNU_ECHO_BINARY = probe_binary('echo')
if GNU_ECHO_BINARY is not None:
    if probe_binary('man') is not None:
        echo_cmd = 'man %s' % os.path.basename(GNU_ECHO_BINARY)
        echo_manpage = process.run(echo_cmd, env={'LANG': 'C'},
                                   encoding='ascii').stdout
        if b'-e' not in echo_manpage:
            GNU_ECHO_BINARY = probe_binary('gecho')
READ_BINARY = probe_binary('read')
SLEEP_BINARY = probe_binary('sleep')


class RunnerOperationTest(TestCaseTmpDir):

    def test_show_version(self):
        result = process.run('%s -v' % AVOCADO, ignore_status=True)
        self.assertEqual(result.exit_status, 0)
        self.assertTrue(re.match(r"^Avocado \d+\.\d+$", result.stdout_text),
                        "Version string does not match 'Avocado \\d\\.\\d:'\n"
                        "%r" % (result.stdout_text))

    def test_alternate_config_datadir(self):
        """
        Uses the "--config" flag to check custom configuration is applied

        Even on the more complex data_dir module, which adds extra checks
        to what is set on the plain settings module.
        """
        base_dir = os.path.join(self.tmpdir.name, 'datadir_base')
        os.mkdir(base_dir)
        mapping = {'base_dir': base_dir,
                   'test_dir': os.path.join(base_dir, 'test'),
                   'data_dir': os.path.join(base_dir, 'data'),
                   'logs_dir': os.path.join(base_dir, 'logs')}
        config = '[datadir.paths]\n'
        for key, value in mapping.items():
            if not os.path.isdir(value):
                os.mkdir(value)
            config += "%s = %s\n" % (key, value)
        fd, config_file = tempfile.mkstemp(dir=self.tmpdir.name)
        os.write(fd, config.encode())
        os.close(fd)

        cmd = '%s --config %s config --datadir' % (AVOCADO, config_file)
        result = process.run(cmd)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn('   base    ' + mapping['base_dir'], result.stdout_text)
        self.assertIn('   data    ' + mapping['data_dir'], result.stdout_text)
        self.assertIn('   logs    ' + mapping['logs_dir'], result.stdout_text)

    def test_runner_phases(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                    'examples/tests/phases.py' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def test_runner_all_ok(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                    'examples/tests/passtest.py examples/tests/passtest.py' % (AVOCADO, self.tmpdir.name))
        process.run(cmd_line)
        # Also check whether jobdata contains correct parameter paths
        variants = open(os.path.join(self.tmpdir.name, "latest", "jobdata",
                                     "variants-1.json")).read()
        expected = '[{"paths": ["/run/*"], "variant_id": null, "variant": [["/", []]]}]'
        self.assertEqual(variants, expected)

    def test_runner_failfast(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                    'examples/tests/passtest.py examples/tests/failtest.py '
                    'examples/tests/passtest.py --failfast '
                    '--nrunner-max-parallel-tasks=1'
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertIn(b'Interrupting job (failfast).', result.stdout)
        self.assertIn(b'PASS 1 | ERROR 0 | FAIL 1 | SKIP 1', result.stdout)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL | exit_codes.AVOCADO_JOB_INTERRUPTED
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def test_runner_ignore_missing_references_one_missing(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                    'examples/tests/passtest.py badtest.py --ignore-missing-references'
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertIn(b'PASS 1 | ERROR 0 | FAIL 0 | SKIP 0', result.stdout)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def test_runner_ignore_missing_references_all_missing(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                    'badtest.py badtest2.py --ignore-missing-references'
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertIn(b'Suite is empty. There is no tests to run.', result.stderr)
        expected_rc = exit_codes.AVOCADO_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def test_runner_test_with_local_imports(self):
        prefix = temp_dir_prefix(self)
        with tempfile.TemporaryDirectory(prefix=prefix) as libdir:
            with script.Script(os.path.join(libdir, 'mylib.py'),
                               "def hello():\n    return 'Hello world'"):
                with script.Script(
                    os.path.join(libdir, 'test_local_imports.py'),
                    ('from avocado import Test\n'
                     'from mylib import hello\n'
                     'class LocalImportTest(Test):\n'
                     '    def test(self):\n'
                     '        self.log.info(hello())\n')) as mytest:
                    cmd_line = ("%s run --disable-sysinfo --job-results-dir %s "
                                "%s" % (AVOCADO, self.tmpdir.name, mytest))
                    process.run(cmd_line)

    def test_unsupported_status(self):
        with script.TemporaryScript("fake_status.py",
                                    UNSUPPORTED_STATUS_TEST_CONTENTS,
                                    "avocado_unsupported_status") as tst:
            res = process.run("%s run --disable-sysinfo --job-results-dir %s %s"
                              " --test-runner=runner"
                              " --json -" % (AVOCADO, self.tmpdir.name, tst),
                              ignore_status=True)
            self.assertEqual(res.exit_status, exit_codes.AVOCADO_TESTS_FAIL)
            results = json.loads(res.stdout_text)
            self.assertEqual(results["tests"][0]["status"], "ERROR",
                             "%s != %s\n%s" % (results["tests"][0]["status"],
                                               "ERROR", res))
            self.assertIn("Runner error occurred: Test reports unsupported",
                          results["tests"][0]["fail_reason"])

    @skipOnLevelsInferiorThan(1)
    def test_hanged_test_with_status(self):
        """Check that avocado handles hanged tests properly.

        :avocado: tags=parallel:1
        """
        with script.TemporaryScript("report_status_and_hang.py",
                                    REPORTS_STATUS_AND_HANG,
                                    "hanged_test_with_status") as tst:
            res = process.run("%s run --disable-sysinfo --job-results-dir %s %s "
                              "--test-runner=runner "
                              "--json - --job-timeout 1" % (AVOCADO, self.tmpdir.name, tst),
                              ignore_status=True)
            self.assertEqual(res.exit_status, exit_codes.AVOCADO_TESTS_FAIL)
            results = json.loads(res.stdout_text)
            self.assertEqual(results["tests"][0]["status"], "ERROR",
                             "%s != %s\n%s" % (results["tests"][0]["status"],
                                               "ERROR", res))
            self.assertIn("Test reported status but did not finish",
                          results["tests"][0]["fail_reason"])
            # Currently it should finish up to 1s after the job-timeout
            # but the prep and postprocess could take a bit longer on
            # some environments, so let's just check it does not take
            # > 60s, which is the deadline for force-finishing the test.
            self.assertLess(res.duration, 55, "Test execution took too long, "
                            "which is likely because the hanged test was not "
                            "interrupted. Results:\n%s" % res)

    def test_no_status_reported(self):
        with script.TemporaryScript("die_without_reporting_status.py",
                                    DIE_WITHOUT_REPORTING_STATUS,
                                    "no_status_reported") as tst:
            res = process.run("%s run --disable-sysinfo --job-results-dir %s %s "
                              "--test-runner=runner "
                              "--json -" % (AVOCADO, self.tmpdir.name, tst),
                              ignore_status=True)
            self.assertEqual(res.exit_status, exit_codes.AVOCADO_TESTS_FAIL)
            results = json.loads(res.stdout_text)
            self.assertEqual(results["tests"][0]["status"], "ERROR",
                             "%s != %s\n%s" % (results["tests"][0]["status"],
                                               "ERROR", res))
            self.assertIn("Test died without reporting the status",
                          results["tests"][0]["fail_reason"])

    def test_runner_tests_fail(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                    'examples/tests/passtest.py '
                    'examples/tests/failtest.py '
                    'examples/tests/passtest.py' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def test_runner_nonexistent_test(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir '
                    '%s bogustest' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        unexpected_rc = exit_codes.AVOCADO_FAIL
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def test_runner_doublefail(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s --xunit - '
                    'examples/tests/doublefail.py' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        unexpected_rc = exit_codes.AVOCADO_FAIL
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))
        self.assertIn(b"TestError: Failing during tearDown. Yay!", result.stdout,
                      "Cleanup exception not printed to log output")
        self.assertIn(b"TestFail: This test is supposed to fail", result.stdout,
                      "Test did not fail with action exception:\n%s" % result.stdout)

    def test_uncaught_exception(self):
        cmd_line = ("%s run --disable-sysinfo --job-results-dir %s "
                    "--json - examples/tests/uncaught_exception.py"
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc,
                                                                result))
        self.assertIn(b'"status": "ERROR"', result.stdout)

    def test_fail_on_exception(self):
        cmd_line = ("%s run --disable-sysinfo --job-results-dir %s "
                    "--json - examples/tests/fail_on_exception.py"
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc,
                                                                result))
        self.assertIn(b'"status": "FAIL"', result.stdout)

    def test_cancel_on_exception(self):
        cmd_line = ("%s run --disable-sysinfo --job-results-dir %s "
                    "--json - examples/tests/cancel_on_exception.py"
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc,
                                                                result))
        result = json.loads(result.stdout_text)
        for test in result['tests']:
            self.assertEqual(test['status'], 'CANCEL')

    def test_assert_raises(self):
        cmd_line = ("%s run --disable-sysinfo --job-results-dir %s "
                    "-- examples/tests/assert.py" % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc,
                                                                result))
        self.assertIn(b'Assert.test_assert_raises:  PASS', result.stdout)
        self.assertIn(b'Assert.test_fails_to_raise:  FAIL', result.stdout)
        self.assertIn(b'PASS 1 | ERROR 0 | FAIL 1 ', result.stdout)

    def test_exception_not_in_path(self):
        os.mkdir(os.path.join(self.tmpdir.name, "shared_lib"))
        mylib = script.Script(os.path.join(self.tmpdir.name, "shared_lib",
                                           "mylib.py"),
                              "from avocado import TestCancel\n\n"
                              "class CancelExc(TestCancel):\n"
                              "    pass")
        mylib.save()
        mytest = script.Script(os.path.join(self.tmpdir.name, "mytest.py"),
                               RAISE_CUSTOM_PATH_EXCEPTION_CONTENT)
        mytest.save()
        result = process.run("%s --show test run --disable-sysinfo "
                             "--test-runner=runner "
                             "--job-results-dir %s %s"
                             % (AVOCADO, self.tmpdir.name, mytest))
        self.assertIn(b"mytest.py:SharedLibTest.test -> CancelExc: This "
                      b"should not crash on unpickling in runner",
                      result.stdout)
        self.assertNotIn(b"Failed to read queue", result.stdout)

    def test_runner_timeout(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                    'examples/tests/timeouttest.py'
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        json_path = os.path.join(self.tmpdir.name, 'latest', 'results.json')
        with open(json_path) as json_file:
            result_json = json.load(json_file)
        output = result.stdout
        expected_rc = exit_codes.AVOCADO_JOB_INTERRUPTED
        unexpected_rc = exit_codes.AVOCADO_FAIL
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))
        self.assertIn("timeout", result_json["tests"][0]["fail_reason"])
        # Ensure no test aborted error messages show up
        self.assertNotIn(b"TestAbortError: Test aborted unexpectedly", output)

    @skipOnLevelsInferiorThan(2)
    def test_runner_abort(self):
        """
        :avocado: tags=parallel:1
        """
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                    '--test-runner=runner '
                    '--xunit - examples/tests/abort.py' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        excerpt = b'Test died without reporting the status.'
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        unexpected_rc = exit_codes.AVOCADO_FAIL
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))
        self.assertIn(excerpt, result.stdout)

    def test_silent_output(self):
        cmd_line = ('%s --show=none run --disable-sysinfo --job-results-dir %s '
                    'examples/tests/passtest.py' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEqual(result.stdout, b'')

    def test_show_user_stream(self):
        cmd_line = ('%s --show=app,avocado.test.progress run --disable-sysinfo '
                    '--job-results-dir %s examples/tests/logging_streams.py' %
                    (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertIn(b'Plant.test_plant_organic: preparing soil on row 0',
                      result.stdout)

    def test_empty_args_list(self):
        cmd_line = AVOCADO
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
        self.assertIn(b'avocado: error: the following arguments are required',
                      result.stderr)

    def test_empty_test_list(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s'
                    '--test-runner=runner ' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_JOB_FAIL)
        self.assertIn(b'No test references provided nor any other arguments '
                      b'resolved into tests', result.stderr)

    def test_not_found(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                    '--test-runner=runner '
                    'sbrubles' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_JOB_FAIL)
        self.assertIn(b'Unable to resolve reference', result.stderr)
        self.assertNotIn(b'Unable to resolve reference', result.stdout)

    def test_invalid_unique_id(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s --force-job-id '
                    'foobar examples/tests/passtest.py' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertNotEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertIn(b'needs to be a 40 digit hex', result.stderr)
        self.assertNotIn(b'needs to be a 40 digit hex', result.stdout)

    def test_valid_unique_id(self):
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    '--force-job-id 975de258ac05ce5e490648dec4753657b7ccc7d1 '
                    'examples/tests/passtest.py' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertNotIn(b'needs to be a 40 digit hex', result.stderr)
        self.assertIn(b'PASS', result.stdout)

    def test_automatic_unique_id(self):
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    'examples/tests/passtest.py --json -' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        r = json.loads(result.stdout_text)
        int(r['job_id'], 16)  # it's an hex number
        self.assertEqual(len(r['job_id']), 40)

    @skipOnLevelsInferiorThan(2)
    def test_early_latest_result(self):
        """
        Tests that the `latest` link to the latest job results is created early

        :avocado: tags=parallel:1
        """
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                    'examples/tests/passtest.py' % (AVOCADO, self.tmpdir.name))
        avocado_process = process.SubProcess(cmd_line)
        try:
            avocado_process.start()
            link = os.path.join(self.tmpdir.name, 'latest')
            for _ in range(0, 50):
                time.sleep(0.1)
                if os.path.exists(link) and os.path.islink(link):
                    avocado_process.wait()
                    break
            self.assertTrue(os.path.exists(link))
            self.assertTrue(os.path.islink(link))
        finally:
            avocado_process.wait()

    def test_invalid_python(self):
        test = script.make_script(os.path.join(self.tmpdir.name, 'test.py'),
                                  INVALID_PYTHON_TEST)
        cmd_line = ('%s --show test run --disable-sysinfo '
                    '--job-results-dir %s '
                    '--test-runner=runner '
                    '%s') % (AVOCADO, self.tmpdir.name, test)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn('1-%s:MyTest.test_my_name -> TestError' % test,
                      result.stdout_text)

    @unittest.skipIf(not READ_BINARY, "read binary not available.")
    @skipOnLevelsInferiorThan(1)
    def test_read(self):
        """
        :avocado: tags=parallel:1
        """
        cmd = "%s run --disable-sysinfo --job-results-dir %%s %%s" % AVOCADO
        cmd %= (self.tmpdir.name, READ_BINARY)
        result = process.run(cmd, timeout=10, ignore_status=True)
        self.assertLess(result.duration, 8, "Duration longer than expected."
                        "\n%s" % result)
        self.assertEqual(result.exit_status, 1, "Expected exit status is 1\n%s"
                         % result)

    def test_runner_test_parameters(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                    '-p "sleep_length=0.01" -- examples/tests/sleeptest.py '
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

        json_path = os.path.join(self.tmpdir.name, 'latest', 'results.json')
        with open(json_path) as json_file:
            result_json = json.load(json_file)
        with open(result_json['tests'][0]['logfile'], 'r+b') as test_log_file:
            test_log = test_log_file.read()

        self.assertIn(b"PARAMS (key=sleep_length, path=*, default=1) => '0.01'",
                      test_log)
        self.assertIn(b"Sleeping for 0.01 seconds", test_log)

    def test_other_loggers(self):
        with script.TemporaryScript(
                'mytest.py',
                TEST_OTHER_LOGGERS_CONTENT,
                'avocado_functional_test_other_loggers') as mytest:

            cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                        '-- %s' % (AVOCADO, self.tmpdir.name, mytest))
            result = process.run(cmd_line, ignore_status=True)
            expected_rc = exit_codes.AVOCADO_ALL_OK
            self.assertEqual(result.exit_status, expected_rc,
                             "Avocado did not return rc %d:\n%s" %
                             (expected_rc, result))

            test_log_dir = glob.glob(os.path.join(self.tmpdir.name, 'job-*',
                                                  'test-results', '1-*'))[0]
            test_log_path = os.path.join(test_log_dir, 'debug.log')
            with open(test_log_path, 'rb') as test_log:
                self.assertNotIn(b'SHOULD NOT BE ON debug.log', test_log.read())

    def test_store_logging_stream(self):
        cmd = ("%s run --job-results-dir %s "
               "--store-logging-stream=avocado.test.progress "
               "--disable-sysinfo -- examples/tests/logging_streams.py"
               % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)

        progress_info = os.path.join(self.tmpdir.name, 'latest', 'test-results',
                                     '1-examples_tests_logging_streams.py_Plant'
                                     '.test_plant_organic',
                                     'avocado.test.progress')
        self.assertTrue(os.path.exists(progress_info))
        with open(progress_info) as file:
            stream_line = file.readline()
            self.assertIn('INFO | 1-examples/tests/logging_streams.py:'
                          'Plant.test_plant_organic: preparing soil on row 0',
                          stream_line)


class DryRunTest(TestCaseTmpDir):

    def test_dry_run(self):
        examples_path = os.path.join('examples', 'tests')
        passtest = os.path.join(examples_path, 'passtest.py')
        failtest = os.path.join(examples_path, 'failtest.py')
        gendata = os.path.join(examples_path, 'gendata.py')
        cmd = ("%s run --disable-sysinfo --dry-run "
               "--dry-run-no-cleanup --json - -- %s %s %s " % (AVOCADO,
                                                               passtest,
                                                               failtest,
                                                               gendata))
        number_of_tests = 3
        result = json.loads(process.run(cmd).stdout_text)
        # Check if all tests were skipped
        self.assertEqual(result['cancel'], number_of_tests)
        for i in range(number_of_tests):
            test = result['tests'][i]
            self.assertEqual(test['fail_reason'],
                             u'Test cancelled due to --dry-run')


class RunnerHumanOutputTest(TestCaseTmpDir):

    def test_output_pass(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                    'examples/tests/passtest.py' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn(b'passtest.py:PassTest.test:  PASS', result.stdout)

    def test_output_fail(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                    'examples/tests/failtest.py' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn(b'examples/tests/failtest.py:FailTest.test:  FAIL',
                      result.stdout)

    def test_output_error(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                    'examples/tests/errortest.py' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn(b'errortest.py:ErrorTest.test:  ERROR', result.stdout)

    def test_output_cancel(self):
        cmd_line = ('%s run --disable-sysinfo --job-results-dir %s '
                    'examples/tests/cancelonsetup.py' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn(b'PASS 0 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | '
                      b'INTERRUPT 0 | CANCEL 1',
                      result.stdout)


class RunnerSimpleTest(TestCaseTmpDir):

    def setUp(self):
        super(RunnerSimpleTest, self).setUp()
        self.pass_script = script.TemporaryScript(
            u'\u00e1 \u00e9 \u00ed \u00f3 \u00fa',
            "#!/bin/sh\ntrue",
            'avocado_simpletest_functional')
        self.pass_script.save()
        self.fail_script = script.TemporaryScript('avocado_fail.sh',
                                                  "#!/bin/sh\nfalse",
                                                  'avocado_simpletest_'
                                                  'functional')
        self.fail_script.save()

    def test_simpletest_pass(self):
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo'
                    ' "%s"' % (AVOCADO, self.tmpdir.name, self.pass_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def test_simpletest_fail(self):
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo'
                    ' %s' % (AVOCADO, self.tmpdir.name, self.fail_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    @skipOnLevelsInferiorThan(2)
    def test_runner_onehundred_fail_timing(self):
        """
        We can be pretty sure that a failtest should return immediately. Let's
        run 100 of them and assure they not take more than 30 seconds to run.

        Notice: on a current machine this takes about 0.12s, so 30 seconds is
        considered to be pretty safe here.

        :avocado: tags=parallel:1
        """
        one_hundred = 'examples/tests/failtest.py ' * 100
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo %s'
                    % (AVOCADO, self.tmpdir.name, one_hundred))
        initial_time = time.monotonic()
        result = process.run(cmd_line, ignore_status=True)
        actual_time = time.monotonic() - initial_time
        self.assertLess(actual_time, 60.0)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    @skipOnLevelsInferiorThan(2)
    def test_runner_sleep_fail_sleep_timing(self):
        """
        Sleeptest is supposed to take 1 second, let's make a sandwich of
        100 failtests and check the test runner timing.

        :avocado: tags=parallel:1
        """
        sleep_fail_sleep = ('examples/tests/sleeptest.py ' +
                            'examples/tests/failtest.py ' * 100 +
                            'examples/tests/sleeptest.py')
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo %s'
                    % (AVOCADO, self.tmpdir.name, sleep_fail_sleep))
        initial_time = time.monotonic()
        result = process.run(cmd_line, ignore_status=True)
        actual_time = time.monotonic() - initial_time
        self.assertLess(actual_time, 63.0)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def test_simplewarning(self):
        """
        simplewarning.sh uses the avocado-bash-utils
        """
        # simplewarning.sh calls "avocado" without specifying a path
        # let's add the path that was defined at the global module
        # scope here
        os.environ['PATH'] += ":" + os.path.dirname(AVOCADO)
        # simplewarning.sh calls "avocado exec-path" which hasn't
        # access to an installed location for the libexec scripts
        os.environ['PATH'] += ":" + os.path.join(BASEDIR, 'libexec')
        cmd_line = ('%s --show=test run --job-results-dir %s --disable-sysinfo '
                    '--test-runner=runner '
                    'examples/tests/simplewarning.sh'
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %s:\n%s" %
                         (expected_rc, result))
        self.assertIn(b'DEBUG| Debug message', result.stdout, result)
        self.assertIn(b'INFO | Info message', result.stdout, result)
        self.assertIn(b'WARN | Warning message (should cause this test to '
                      b'finish with warning)', result.stdout, result)
        self.assertIn(b'ERROR| Error message (ordinary message not changing '
                      b'the results)', result.stdout, result)
        self.assertIn(b'Test passed but there were warnings', result.stdout,
                      result)

    def test_non_absolute_path(self):
        test_base_dir = os.path.dirname(self.pass_script.path)
        os.chdir(test_base_dir)
        test_file_name = os.path.basename(self.pass_script.path)
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo'
                    ' --test-runner=runner'
                    ' "%s"' % (AVOCADO, self.tmpdir.name,
                               test_file_name))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def tearDown(self):
        self.pass_script.remove()
        self.fail_script.remove()
        super(RunnerSimpleTest, self).tearDown()


class RunnerSimpleTestStatus(TestCaseTmpDir):

    def setUp(self):
        super(RunnerSimpleTestStatus, self).setUp()
        self.config_file = script.TemporaryScript('avocado.conf',
                                                  "[simpletests.status]\n"
                                                  "warn_regex = ^WARN$\n"
                                                  "skip_regex = ^SKIP$\n"
                                                  "skip_location = stdout\n")
        self.config_file.save()

    def test_simpletest_status(self):
        # Multi-line warning in STDERR should by default be handled
        warn_script = script.TemporaryScript('avocado_warn.sh',
                                             '#!/bin/sh\n'
                                             '>&2 echo -e "\\n\\nWARN\\n"',
                                             'avocado_simpletest_'
                                             'functional')
        warn_script.save()
        cmd_line = ('%s --config %s run --job-results-dir %s --disable-sysinfo'
                    ' --test-runner=runner'
                    ' %s --json -' % (AVOCADO, self.config_file.path,
                                      self.tmpdir.name, warn_script.path))
        result = process.run(cmd_line, ignore_status=True)
        json_results = json.loads(result.stdout_text)
        self.assertEqual(json_results['tests'][0]['status'], 'WARN')
        warn_script.remove()
        # Skip in STDOUT should be handled because of config
        skip_script = script.TemporaryScript('avocado_skip.sh',
                                             "#!/bin/sh\necho SKIP",
                                             'avocado_simpletest_'
                                             'functional')
        skip_script.save()
        cmd_line = ('%s --config %s run --job-results-dir %s --disable-sysinfo'
                    ' --test-runner=runner'
                    ' %s --json -' % (AVOCADO, self.config_file.path,
                                      self.tmpdir.name, skip_script.path))
        result = process.run(cmd_line, ignore_status=True)
        json_results = json.loads(result.stdout_text)
        self.assertEqual(json_results['tests'][0]['status'], 'SKIP')
        skip_script.remove()
        # STDERR skip should not be handled
        skip2_script = script.TemporaryScript('avocado_skip.sh',
                                              "#!/bin/sh\n>&2 echo SKIP",
                                              'avocado_simpletest_'
                                              'functional')
        skip2_script.save()
        cmd_line = ('%s --config %s run --job-results-dir %s --disable-sysinfo'
                    ' --test-runner=runner'
                    ' %s --json -' % (AVOCADO, self.config_file.path,
                                      self.tmpdir.name, skip2_script.path))
        result = process.run(cmd_line, ignore_status=True)
        json_results = json.loads(result.stdout_text)
        self.assertEqual(json_results['tests'][0]['status'], 'PASS')
        skip2_script.remove()

    def tearDown(self):
        super(RunnerSimpleTestStatus, self).tearDown()
        self.config_file.remove()


class RunnerReferenceFromConfig(TestCaseTmpDir):

    def setUp(self):
        super(RunnerReferenceFromConfig, self).setUp()
        self.config_file = script.TemporaryScript('avocado.conf',
                                                  "[resolver]\n"
                                                  "references = ['/bin/true']\n")
        self.config_file.save()

    @skipUnlessPathExists('/bin/true')
    def test(self):
        cmd_line = '%s --config %s run --job-results-dir %s --disable-sysinfo'
        cmd_line %= (AVOCADO, self.config_file.path, self.tmpdir.name)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    def tearDown(self):
        super(RunnerReferenceFromConfig, self).tearDown()
        self.config_file.remove()


class RunnerSimpleTestFailureFields(TestCaseTmpDir):

    def setUp(self):
        super(RunnerSimpleTestFailureFields, self).setUp()
        self.config_file = script.TemporaryScript(
            'avocado.conf',
            "[simpletests.status]\n"
            "failure_fields = ['stdout', 'stderr']\n")
        self.config_file.save()

    def test_simpletest_failure_fields(self):
        fail_test = os.path.join(BASEDIR, 'examples', 'tests', 'failtest.sh')
        cmd_line = ('%s --config %s run --job-results-dir %s --disable-sysinfo'
                    ' --test-runner=runner'
                    ' -- %s' % (AVOCADO, self.config_file.path,
                                self.tmpdir.name, fail_test))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))
        self.assertNotIn("Exited with status: '1'", result.stdout_text)

    def tearDown(self):
        super(RunnerSimpleTestFailureFields, self).tearDown()
        self.config_file.remove()


class PluginsTest(TestCaseTmpDir):

    def test_sysinfo_plugin(self):
        cmd_line = '%s sysinfo %s' % (AVOCADO, self.tmpdir.name)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        sysinfo_files = os.listdir(self.tmpdir.name)
        self.assertGreater(len(sysinfo_files), 0, "Empty sysinfo files dir")

    def test_list_plugin(self):
        cmd_line = '%s list' % AVOCADO
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn(b'No tests were found on current tests dir',
                         result.stdout)

    def test_list_error_output(self):
        cmd_line = '%s list --loader sbrubles' % AVOCADO
        result = process.run(cmd_line, ignore_status=True)
        self.assertIn(b"Unable to resolve reference", result.stderr)

    def test_list_no_file_loader(self):
        cmd_line = ("%s --verbose list --loaders tap.TAP "
                    "--loader "
                    "-- this-wont-be-matched" % AVOCADO)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK,
                         "Avocado did not return rc %d:\n%s"
                         % (exit_codes.AVOCADO_ALL_OK, result))
        exp = (b"Type    Test                 Tag(s)\n"
               b"MISSING this-wont-be-matched\n\n"
               b"TEST TYPES SUMMARY\n"
               b"==================\n"
               b"missing: 1\n")
        self.assertEqual(exp, result.stdout, "Stdout mismatch:\n%s\n\n%s"
                         % (exp, result))

    def test_list_verbose_tags(self):
        """
        Runs list verbosely and check for tag related output
        """
        test = script.make_script(os.path.join(self.tmpdir.name, 'test.py'),
                                  VALID_PYTHON_TEST_WITH_TAGS)
        cmd_line = ("%s --verbose list "
                    "--loader "
                    "--loaders file -- %s" % (AVOCADO, test))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK,
                         "Avocado did not return rc %d:\n%s"
                         % (exit_codes.AVOCADO_ALL_OK, result))
        stdout_lines = result.stdout_text.splitlines()
        self.assertIn("Tag(s)", stdout_lines[0])
        full_test_name = "%s:MyTest.test" % test
        self.assertEqual("INSTRUMENTED %s BIG_TAG_NAME" % full_test_name,
                         stdout_lines[1])
        self.assertIn("TEST TYPES SUMMARY", stdout_lines)
        self.assertIn("instrumented: 1", stdout_lines)
        self.assertIn("TEST TAGS SUMMARY", stdout_lines)
        self.assertEqual("big_tag_name: 1", stdout_lines[-1])

    def test_plugin_list(self):
        cmd_line = '%s plugins' % AVOCADO
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn(b'Disabled', result.stdout)

    def test_config_plugin(self):
        cmd_line = '%s config ' % AVOCADO
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn(b'Disabled', result.stdout)

    def test_config_plugin_datadir(self):
        cmd_line = '%s config --datadir ' % AVOCADO
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn(b'Disabled', result.stdout)

    def test_disable_plugin(self):
        cmd_line = '%s plugins' % AVOCADO
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn(b"Collect system information", result.stdout)

        config_content = "[plugins]\ndisable=['cli.cmd.sysinfo',]"
        config = script.TemporaryScript("disable_sysinfo_cmd.conf",
                                        config_content)
        with config:
            cmd_line = '%s --config %s plugins' % (AVOCADO, config)
            result = process.run(cmd_line, ignore_status=True)
            expected_rc = exit_codes.AVOCADO_ALL_OK
            self.assertEqual(result.exit_status, expected_rc,
                             "Avocado did not return rc %d:\n%s" %
                             (expected_rc, result))
            self.assertNotIn(b"Collect system information", result.stdout)

    def test_plugin_order(self):
        """
        Tests plugin order by configuration file

        First it checks if html, json, xunit and zip_archive plugins are enabled.
        Then it runs a test with zip_archive running first, which means the html,
        json and xunit output files do not make into the archive.

        Then it runs with zip_archive set to run last, which means the html,
        json and xunit output files *do* make into the archive.
        """
        def run_config(config_path):
            cmd = ('%s --config %s run examples/tests/passtest.py --archive '
                   '--job-results-dir %s --disable-sysinfo'
                   % (AVOCADO, config_path, self.tmpdir.name))
            result = process.run(cmd, ignore_status=True)
            expected_rc = exit_codes.AVOCADO_ALL_OK
            self.assertEqual(result.exit_status, expected_rc,
                             "Avocado did not return rc %d:\n%s" %
                             (expected_rc, result))

        result_plugins = ["json", "xunit", "zip_archive"]
        result_outputs = ["results.json", "results.xml"]
        if python_module_available('avocado-framework-plugin-result-html'):
            result_plugins.append("html")
            result_outputs.append("results.html")

        cmd_line = '%s plugins' % AVOCADO
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        for result_plugin in result_plugins:
            self.assertIn(result_plugin, result.stdout_text)

        config_content_zip_first = "[plugins.result]\norder=['zip_archive']"
        config_zip_first = script.TemporaryScript("zip_first.conf",
                                                  config_content_zip_first)
        with config_zip_first:
            run_config(config_zip_first)
            archives = glob.glob(os.path.join(self.tmpdir.name, '*.zip'))
            self.assertEqual(len(archives), 1, "ZIP Archive not generated")
            zip_file = zipfile.ZipFile(archives[0], 'r')
            zip_file_list = zip_file.namelist()
            for result_output in result_outputs:
                self.assertNotIn(result_output, zip_file_list)
            os.unlink(archives[0])

        config_content_zip_last = ("[plugins.result]\norder=['html', 'json',"
                                   "'xunit', 'non_existing_plugin_is_ignored'"
                                   ",'zip_archive']")
        config_zip_last = script.TemporaryScript("zip_last.conf",
                                                 config_content_zip_last)
        with config_zip_last:
            run_config(config_zip_last)
            archives = glob.glob(os.path.join(self.tmpdir.name, '*.zip'))
            self.assertEqual(len(archives), 1, "ZIP Archive not generated")
            zip_file = zipfile.ZipFile(archives[0], 'r')
            zip_file_list = zip_file.namelist()
            for result_output in result_outputs:
                self.assertIn(result_output, zip_file_list)

    def test_Namespace_object_has_no_attribute(self):
        cmd_line = '%s plugins' % AVOCADO
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn(b"'Namespace' object has no attribute", result.stderr)


class ParseXMLError(Exception):
    pass


class PluginsXunitTest(TestCaseTmpDir):

    @unittest.skipUnless(SCHEMA_CAPABLE,
                         'Unable to validate schema due to missing xmlschema library')
    def setUp(self):
        super(PluginsXunitTest, self).setUp()
        junit_xsd = os.path.join(os.path.dirname(__file__),
                                 os.path.pardir, ".data", 'jenkins-junit.xsd')
        self.xml_schema = xmlschema.XMLSchema(junit_xsd)

    def run_and_check(self, testname, e_rc, e_ntests, e_nerrors,
                      e_nfailures, e_nskip):
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo'
                    ' --test-runner=runner'
                    ' --xunit - %s' % (AVOCADO, self.tmpdir.name, testname))
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

        # pylint: disable=I1101
        xunit_file_output = os.path.join(self.tmpdir.name, 'latest', 'results.xml')
        self.assertTrue(self.xml_schema.is_valid(xunit_file_output))

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
        self.run_and_check('examples/tests/passtest.py',
                           exit_codes.AVOCADO_ALL_OK,
                           1, 0, 0, 0)

    def test_xunit_plugin_failtest(self):
        self.run_and_check('examples/tests/failtest.py',
                           exit_codes.AVOCADO_TESTS_FAIL,
                           1, 0, 1, 0)

    def test_xunit_plugin_skiponsetuptest(self):
        self.run_and_check('examples/tests/cancelonsetup.py',
                           exit_codes.AVOCADO_ALL_OK,
                           1, 0, 0, 1)

    def test_xunit_plugin_errortest(self):
        self.run_and_check('examples/tests/errortest.py',
                           exit_codes.AVOCADO_TESTS_FAIL,
                           1, 1, 0, 0)


class ParseJSONError(Exception):
    pass


class PluginsJSONTest(TestCaseTmpDir):

    def run_and_check(self, testname, e_rc, e_ntests, e_nerrors,
                      e_nfailures, e_nskip, e_ncancel=0):
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    '--test-runner=runner '
                    '--json - --archive %s' % (AVOCADO, self.tmpdir.name, testname))
        result = process.run(cmd_line, ignore_status=True)
        json_output = result.stdout_text
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
        n_cancel = json_data['cancel']
        self.assertEqual(n_cancel, e_ncancel)
        return json_data

    def test_json_plugin_passtest(self):
        self.run_and_check('examples/tests/passtest.py',
                           exit_codes.AVOCADO_ALL_OK,
                           1, 0, 0, 0)

    def test_json_plugin_failtest(self):
        self.run_and_check('examples/tests/failtest.py',
                           exit_codes.AVOCADO_TESTS_FAIL,
                           1, 0, 1, 0)

    def test_json_plugin_skiponsetuptest(self):
        self.run_and_check('examples/tests/cancelonsetup.py',
                           exit_codes.AVOCADO_ALL_OK,
                           1, 0, 0, 0, 1)

    def test_json_plugin_errortest(self):
        self.run_and_check('examples/tests/errortest.py',
                           exit_codes.AVOCADO_TESTS_FAIL,
                           1, 1, 0, 0)


if __name__ == '__main__':
    unittest.main()
