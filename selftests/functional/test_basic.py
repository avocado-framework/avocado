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
        echo_cmd = f'man {os.path.basename(GNU_ECHO_BINARY)}'
        echo_manpage = process.run(echo_cmd, env={'LANG': 'C'},
                                   encoding='ascii').stdout
        if b'-e' not in echo_manpage:
            GNU_ECHO_BINARY = probe_binary('gecho')
READ_BINARY = probe_binary('read')
SLEEP_BINARY = probe_binary('sleep')


class RunnerOperationTest(TestCaseTmpDir):

    def test_show_version(self):
        result = process.run(f'{AVOCADO} -v', ignore_status=True)
        self.assertEqual(result.exit_status, 0)
        self.assertTrue(re.match(r"^Avocado \d+\.\d+$", result.stdout_text),
                        (f"Version string does not match "
                         f"'Avocado \\d\\.\\d:'\n"
                         f"{result.stdout_text}"))

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
            config += f"{key} = {value}\n"
        fd, config_file = tempfile.mkstemp(dir=self.tmpdir.name)
        os.write(fd, config.encode())
        os.close(fd)

        cmd = f'{AVOCADO} --config {config_file} config --datadir'
        result = process.run(cmd)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         (f"Avocado did not return rc {expected_rc}:"
                          f"\n{result}"))
        self.assertIn('   base    ' + mapping['base_dir'], result.stdout_text)
        self.assertIn('   data    ' + mapping['data_dir'], result.stdout_text)
        self.assertIn('   logs    ' + mapping['logs_dir'], result.stdout_text)

    def test_runner_phases(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo '
                    f'--job-results-dir {self.tmpdir.name} '
                    f'examples/tests/phases.py')
        result = process.run(cmd_line)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         (f"Avocado did not return rc {expected_rc}:"
                          f"\n{result}"))

    def test_runner_all_ok(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo '
                    f'--job-results-dir {self.tmpdir.name} '
                    f'examples/tests/passtest.py examples/tests/passtest.py')
        process.run(cmd_line)
        # Also check whether jobdata contains correct parameter paths
        variants = open(os.path.join(self.tmpdir.name, "latest", "jobdata",
                                     "variants-1.json"), encoding='utf-8').read()
        expected = '[{"paths": ["/run/*"], "variant_id": null, "variant": [["/", []]]}]'
        self.assertEqual(variants, expected)

    def test_runner_failfast_fail(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo '
                    f'--job-results-dir {self.tmpdir.name} '
                    f'examples/tests/passtest.py examples/tests/failtest.py '
                    f'examples/tests/passtest.py --failfast '
                    f'--nrunner-max-parallel-tasks=1')
        result = process.run(cmd_line, ignore_status=True)
        self.assertIn(b'Interrupting job (failfast).', result.stdout)
        self.assertIn(b'PASS 1 | ERROR 0 | FAIL 1 | SKIP 1', result.stdout)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL | exit_codes.AVOCADO_JOB_INTERRUPTED
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

    def test_runner_failfast_error(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo '
                    f'--job-results-dir {self.tmpdir.name} '
                    f'examples/tests/passtest.py examples/tests/errortest.py '
                    f'examples/tests/passtest.py --failfast '
                    f'--nrunner-max-parallel-tasks=1')
        result = process.run(cmd_line, ignore_status=True)
        self.assertIn(b'Interrupting job (failfast).', result.stdout)
        self.assertIn(b'PASS 1 | ERROR 1 | FAIL 0 | SKIP 1', result.stdout)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL | exit_codes.AVOCADO_JOB_INTERRUPTED
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

    def test_runner_ignore_missing_references_one_missing(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo '
                    f'--job-results-dir {self.tmpdir.name} '
                    f'examples/tests/passtest.py badtest.py '
                    f'--ignore-missing-references')
        result = process.run(cmd_line, ignore_status=True)
        self.assertIn(b'PASS 1 | ERROR 0 | FAIL 0 | SKIP 0', result.stdout)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

    def test_runner_ignore_missing_references_all_missing(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo '
                    f'--job-results-dir {self.tmpdir.name} '
                    f'badtest.py badtest2.py --ignore-missing-references')
        result = process.run(cmd_line, ignore_status=True)
        self.assertIn(b'Suite is empty. There is no tests to run.', result.stderr)
        expected_rc = exit_codes.AVOCADO_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

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
                    cmd_line = (f'{AVOCADO} run --disable-sysinfo '
                                f'--job-results-dir {self.tmpdir.name} '
                                f'{mytest}')
                    process.run(cmd_line)

    def test_unsupported_status(self):
        with script.TemporaryScript("fake_status.py",
                                    UNSUPPORTED_STATUS_TEST_CONTENTS,
                                    "avocado_unsupported_status") as tst:
            res = process.run((f"{AVOCADO} run --disable-sysinfo "
                               f"--job-results-dir {self.tmpdir.name} {tst} "
                               f"--json -"),
                              ignore_status=True)
            self.assertEqual(res.exit_status, exit_codes.AVOCADO_TESTS_FAIL)
            results = json.loads(res.stdout_text)
            self.assertEqual(results["tests"][0]["status"], "ERROR",
                             (f"{results['tests'][0]['status']} != "
                              f"{'ERROR'}\n{res}"))
            self.assertIn("Runner error occurred: Test reports unsupported",
                          results["tests"][0]["fail_reason"])

    def test_runner_tests_fail(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo --job-results-dir '
                    f'{self.tmpdir.name} examples/tests/passtest.py '
                    f'examples/tests/failtest.py examples/tests/passtest.py')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

    def test_runner_nonexistent_test(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo --job-results-dir '
                    f'{self.tmpdir.name} bogustest')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        unexpected_rc = exit_codes.AVOCADO_FAIL
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            f"Avocado crashed (rc {unexpected_rc}):\n{result}")
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

    def test_runner_doublefail(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo --job-results-dir '
                    f'{self.tmpdir.name} --xunit - '
                    f'examples/tests/doublefail.py')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        unexpected_rc = exit_codes.AVOCADO_FAIL
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            f"Avocado crashed (rc {unexpected_rc}):\n{result}")
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertIn(b"TestError: Failing during tearDown. Yay!", result.stdout,
                      "Cleanup exception not printed to log output")
        self.assertIn(b"TestFail: This test is supposed to fail", result.stdout,
                      (f"Test did not fail with action exception:"
                       f"\n{result.stdout}"))

    def test_uncaught_exception(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo --job-results-dir '
                    f'{self.tmpdir.name} --json - '
                    f'examples/tests/uncaught_exception.py')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertIn(b'"status": "ERROR"', result.stdout)

    def test_fail_on_exception(self):
        cmd_line = (f'{AVOCADO}  run --disable-sysinfo --job-results-dir '
                    f'{self.tmpdir.name} --json - '
                    f'examples/tests/fail_on_exception.py')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertIn(b'"status": "FAIL"', result.stdout)

    def test_cancel_on_exception(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo --job-results-dir '
                    f'{self.tmpdir.name} --json - '
                    f'examples/tests/cancel_on_exception.py')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

        result = json.loads(result.stdout_text)
        for test in result['tests']:
            self.assertEqual(test['status'], 'CANCEL')

    def test_assert_raises(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo --job-results-dir '
                    f'{self.tmpdir.name} -- examples/tests/assert.py')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

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
        result = process.run(f'{AVOCADO} --show test run --disable-sysinfo '
                             f'--job-results-dir {self.tmpdir.name} {mytest}')
        self.assertIn(b"'fail_reason': 'This should not crash on "
                      b"unpickling in runner'", result.stdout)

    def test_runner_timeout(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo --job-results-dir '
                    f'{self.tmpdir.name} examples/tests/timeouttest.py')
        result = process.run(cmd_line, ignore_status=True)
        json_path = os.path.join(self.tmpdir.name, 'latest', 'results.json')
        with open(json_path, encoding='utf-8') as json_file:
            result_json = json.load(json_file)
        output = result.stdout
        expected_rc = exit_codes.AVOCADO_JOB_INTERRUPTED
        unexpected_rc = exit_codes.AVOCADO_FAIL
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            f"Avocado crashed (rc {unexpected_rc}):\n{result}")
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertIn("timeout", result_json["tests"][0]["fail_reason"])
        # Ensure no test aborted error messages show up
        self.assertNotIn(b"TestAbortError: Test aborted unexpectedly", output)

    def test_silent_output(self):
        cmd_line = (f'{AVOCADO} --show=none run --disable-sysinfo '
                    f'--job-results-dir {self.tmpdir.name} '
                    f'examples/tests/passtest.py')
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEqual(result.stdout, b'')

    def test_show_user_stream(self):
        cmd_line = (f'{AVOCADO} --show=app,avocado.test.progress run '
                    f'--disable-sysinfo --job-results-dir {self.tmpdir.name} '
                    f'examples/tests/logging_streams.py')
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
        cmd_line = (f'{AVOCADO} run --disable-sysinfo --job-results-dir '
                    f'{self.tmpdir.name}')
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_JOB_FAIL)
        self.assertEqual(result.stderr,
                         (b'Test Suite could not be created. No test references'
                          b' provided nor any other arguments resolved into '
                          b'tests\n'))

    def test_not_found(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo --job-results-dir '
                    f'{self.tmpdir.name} sbrubles')
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_JOB_FAIL)
        self.assertEqual(result.stdout, b'')
        self.assertEqual(result.stderr,
                         b'Could not resolve references: sbrubles\n')

    def test_invalid_unique_id(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo '
                    f'--job-results-dir {self.tmpdir.name} '
                    f'--force-job-id foobar examples/tests/passtest.py')
        result = process.run(cmd_line, ignore_status=True)
        self.assertNotEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertIn(b'needs to be a 40 digit hex', result.stderr)
        self.assertNotIn(b'needs to be a 40 digit hex', result.stdout)

    def test_valid_unique_id(self):
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo '
                    f'--force-job-id 975de258ac05ce5e490648dec4753657b7ccc7d1 '
                    f'examples/tests/passtest.py')
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertNotIn(b'needs to be a 40 digit hex', result.stderr)
        self.assertIn(b'PASS', result.stdout)

    def test_automatic_unique_id(self):
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo examples/tests/passtest.py --json -')
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
        cmd_line = (f'{AVOCADO} run --disable-sysinfo '
                    f'--job-results-dir {self.tmpdir.name} '
                    f'examples/tests/passtest.py')
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
        cmd_line = (f'{AVOCADO} run --disable-sysinfo '
                    f'--job-results-dir {self.tmpdir.name} {test}')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertIn(f'{test}:MyTest.test_my_name:  ERROR',
                      result.stdout_text)

    @unittest.skipIf(not READ_BINARY, "read binary not available.")
    @skipOnLevelsInferiorThan(1)
    def test_read(self):
        """
        :avocado: tags=parallel:1
        """
        cmd = (f'{AVOCADO} run --disable-sysinfo '
               f'--job-results-dir {self.tmpdir.name} '
               f'{READ_BINARY}')
        result = process.run(cmd, timeout=10, ignore_status=True)
        self.assertLess(result.duration, 8, (f"Duration longer than expected."
                                             f"\n{result}"))
        self.assertEqual(result.exit_status, 1, (f"Expected exit status is 1"
                                                 f"\n{result}"))

    def test_runner_test_parameters(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo --job-results-dir '
                    f'{self.tmpdir.name} -p "sleep_length=0.01" -- '
                    f'examples/tests/sleeptest.py ')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

        json_path = os.path.join(self.tmpdir.name, 'latest', 'results.json')
        with open(json_path, encoding='utf-8') as json_file:
            result_json = json.load(json_file)
        with open(result_json['tests'][0]['logfile'], 'r+b') as test_log_file:  # pylint: disable=W1514
            test_log = test_log_file.read()

        self.assertIn(b"PARAMS (key=sleep_length, path=*, default=1) => '0.01'",
                      test_log)
        self.assertIn(b"Sleeping for 0.01 seconds", test_log)

    def test_other_loggers(self):
        with script.TemporaryScript(
                'mytest.py',
                TEST_OTHER_LOGGERS_CONTENT,
                'avocado_functional_test_other_loggers') as mytest:

            cmd_line = (f'{AVOCADO} run --disable-sysinfo '
                        f'--job-results-dir {self.tmpdir.name} -- {mytest}')
            result = process.run(cmd_line, ignore_status=True)
            expected_rc = exit_codes.AVOCADO_ALL_OK
            self.assertEqual(result.exit_status, expected_rc,
                             (f"Avocado did not return rc {expected_rc}:"
                              f"\n{result}"))

            test_log_dir = glob.glob(os.path.join(self.tmpdir.name, 'job-*',
                                                  'test-results', '1-*'))[0]
            test_log_path = os.path.join(test_log_dir, 'debug.log')
            with open(test_log_path, 'rb') as test_log:  # pylint: disable=W1514
                self.assertNotIn(b'SHOULD NOT BE ON debug.log', test_log.read())

    def test_store_logging_stream(self):
        cmd = (f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
               f"--store-logging-stream=avocado.test.progress "
               f"--disable-sysinfo -- examples/tests/logging_streams.py")
        result = process.run(cmd)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)

        progress_info = os.path.join(self.tmpdir.name, 'latest', 'test-results',
                                     '1-examples_tests_logging_streams.py_Plant'
                                     '.test_plant_organic',
                                     'avocado.test.progress')
        self.assertTrue(os.path.exists(progress_info))
        with open(progress_info, encoding='utf-8') as file:
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
        cmd = (f"{AVOCADO} run --disable-sysinfo --dry-run "
               f"--dry-run-no-cleanup --json - "
               f"-- {passtest} {failtest} {gendata}")
        number_of_tests = 3
        result = json.loads(process.run(cmd).stdout_text)
        # Check if all tests were skipped
        self.assertEqual(result['cancel'], number_of_tests)
        for i in range(number_of_tests):
            test = result['tests'][i]
            self.assertEqual(test['fail_reason'],
                             'Test cancelled due to --dry-run')


class RunnerHumanOutputTest(TestCaseTmpDir):

    def test_output_pass(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo --job-results-dir '
                    f'{self.tmpdir.name} examples/tests/passtest.py')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertIn(b'passtest.py:PassTest.test:  PASS', result.stdout)

    def test_output_fail(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo --job-results-dir '
                    f'{self.tmpdir.name} examples/tests/failtest.py')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertIn(b'examples/tests/failtest.py:FailTest.test:  FAIL', result.stdout)

    def test_output_error(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo --job-results-dir '
                    f'{self.tmpdir.name} examples/tests/errortest.py')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertIn(b'errortest.py:ErrorTest.test:  ERROR', result.stdout)

    def test_output_cancel(self):
        cmd_line = (f'{AVOCADO} run --disable-sysinfo --job-results-dir '
                    f'{self.tmpdir.name} examples/tests/cancelonsetup.py')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertIn(b'PASS 0 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | '
                      b'INTERRUPT 0 | CANCEL 1',
                      result.stdout)


class RunnerExecTest(TestCaseTmpDir):

    def setUp(self):
        super().setUp()
        self.pass_script = script.TemporaryScript(
            '\u00e1 \u00e9 \u00ed \u00f3 \u00fa',
            "#!/bin/sh\ntrue",
            'avocado_exec_test_functional')
        self.pass_script.save()
        self.fail_script = script.TemporaryScript('avocado_fail.sh',
                                                  "#!/bin/sh\nfalse",
                                                  'avocado_exec_test_'
                                                  'functional')
        self.fail_script.save()

    def test_exec_test_pass(self):
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo "{self.pass_script.path}"')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

    def test_exec_test_fail(self):
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {self.fail_script.path}')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

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
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {one_hundred}')
        initial_time = time.monotonic()
        result = process.run(cmd_line, ignore_status=True)
        actual_time = time.monotonic() - initial_time
        self.assertLess(actual_time, 60.0)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

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
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {sleep_fail_sleep}')
        initial_time = time.monotonic()
        result = process.run(cmd_line, ignore_status=True)
        actual_time = time.monotonic() - initial_time
        self.assertLess(actual_time, 63.0)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

    def test_non_absolute_path(self):
        test_base_dir = os.path.dirname(self.pass_script.path)
        os.chdir(test_base_dir)
        test_file_name = os.path.basename(self.pass_script.path)
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo  "{test_file_name}"')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

    def tearDown(self):
        self.pass_script.remove()
        self.fail_script.remove()
        super().tearDown()


class RunnerReferenceFromConfig(TestCaseTmpDir):

    def setUp(self):
        super().setUp()
        self.config_file = script.TemporaryScript('avocado.conf',
                                                  "[resolver]\n"
                                                  "references = ['/bin/true']\n")
        self.config_file.save()

    @skipUnlessPathExists('/bin/true')
    def test(self):
        cmd_line = (f'{AVOCADO} --config {self.config_file.path} run '
                    f'--job-results-dir {self.tmpdir.name} --disable-sysinfo ')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

    def tearDown(self):
        super().tearDown()
        self.config_file.remove()


class RunnerExecTestFailureFields(TestCaseTmpDir):

    def setUp(self):
        super().setUp()
        self.config_file = script.TemporaryScript(
            'avocado.conf',
            "[simpletests.status]\n"
            "failure_fields = ['stdout', 'stderr']\n")
        self.config_file.save()

    def test_exec_test_failure_fields(self):
        fail_test = os.path.join(BASEDIR, 'examples', 'tests', 'failtest.sh')
        cmd_line = (f'{AVOCADO} --config {self.config_file.path} run '
                    f'--job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo -- {fail_test}')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertNotIn("Exited with status: '1'", result.stdout_text)

    def tearDown(self):
        super().tearDown()
        self.config_file.remove()


class PluginsTest(TestCaseTmpDir):

    def test_sysinfo_plugin(self):
        cmd_line = f'{AVOCADO} sysinfo {self.tmpdir.name}'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        sysinfo_files = os.listdir(self.tmpdir.name)
        self.assertGreater(len(sysinfo_files), 0, "Empty sysinfo files dir")

    def test_list_plugin(self):
        cmd_line = f'{AVOCADO} list'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertNotIn(b'No tests were found on current tests dir',
                         result.stdout)

    def test_list_error_output(self):
        cmd_line = f'{AVOCADO} list sbrubles'
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual("", result.stdout_text)

    def test_plugin_list(self):
        cmd_line = f'{AVOCADO} plugins'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertNotIn(b'Disabled', result.stdout)

    def test_config_plugin(self):
        cmd_line = f'{AVOCADO} config '
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertNotIn(b'Disabled', result.stdout)

    def test_config_plugin_datadir(self):
        cmd_line = f'{AVOCADO} config --datadir '
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertNotIn(b'Disabled', result.stdout)

    def test_disable_plugin(self):
        cmd_line = f'{AVOCADO} plugins'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertIn(b"Collect system information", result.stdout)

        config_content = "[plugins]\ndisable=['cli.cmd.sysinfo',]"
        config = script.TemporaryScript("disable_sysinfo_cmd.conf",
                                        config_content)
        with config:
            cmd_line = f'{AVOCADO} --config {config} plugins'
            result = process.run(cmd_line, ignore_status=True)
            expected_rc = exit_codes.AVOCADO_ALL_OK
            self.assertEqual(result.exit_status, expected_rc,
                             (f"Avocado did not return rc {expected_rc}:"
                              f"\n{result}"))
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
            cmd = (f'{AVOCADO} --config {config_path} '
                   f'run examples/tests/passtest.py --archive '
                   f'--job-results-dir {self.tmpdir.name} '
                   f'--disable-sysinfo')
            result = process.run(cmd, ignore_status=True)
            expected_rc = exit_codes.AVOCADO_ALL_OK
            self.assertEqual(result.exit_status, expected_rc,
                             (f"Avocado did not return rc {expected_rc}:"
                              f"\n{result}"))

        result_plugins = ["json", "xunit", "zip_archive"]
        result_outputs = ["results.json", "results.xml"]
        if python_module_available('avocado-framework-plugin-result-html'):
            result_plugins.append("html")
            result_outputs.append("results.html")

        cmd_line = f'{AVOCADO} plugins'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
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
        cmd_line = f'{AVOCADO} plugins'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertNotIn(b"'Namespace' object has no attribute", result.stderr)


class ParseXMLError(Exception):
    pass


class PluginsXunitTest(TestCaseTmpDir):

    @unittest.skipUnless(SCHEMA_CAPABLE,
                         'Unable to validate schema due to missing xmlschema library')
    def setUp(self):
        super().setUp()
        junit_xsd = os.path.join(os.path.dirname(__file__),
                                 os.path.pardir, ".data", 'jenkins-junit.xsd')
        self.xml_schema = xmlschema.XMLSchema(junit_xsd)

    def run_and_check(self, testname, e_rc, e_ntests, e_nerrors,
                      e_nfailures, e_nskip):
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo '
                    f'--xunit - {testname}')
        result = process.run(cmd_line, ignore_status=True)
        xml_output = result.stdout
        self.assertEqual(result.exit_status, e_rc,
                         f"Avocado did not return rc {e_rc}:\n{result}")
        try:
            xunit_doc = xml.dom.minidom.parseString(xml_output)
        except Exception as detail:
            raise ParseXMLError(f"Failed to parse content: {detail}\n{xml_output}")

        # pylint: disable=I1101
        xunit_file_output = os.path.join(self.tmpdir.name, 'latest', 'results.xml')
        self.assertTrue(self.xml_schema.is_valid(xunit_file_output))

        testsuite_list = xunit_doc.getElementsByTagName('testsuite')
        self.assertEqual(len(testsuite_list), 1, 'More than one testsuite tag')

        testsuite_tag = testsuite_list[0]
        self.assertEqual(len(testsuite_tag.attributes), 7,
                         (f'The testsuite tag does not have 7 attributes. '
                          f'XML:\n{xml_output}'))

        n_tests = int(testsuite_tag.attributes['tests'].value)
        self.assertEqual(n_tests, e_ntests,
                         (f"Unexpected number of executed tests, XML:\n"
                          f"{xml_output}"))

        n_errors = int(testsuite_tag.attributes['errors'].value)
        self.assertEqual(n_errors, e_nerrors,
                         (f"Unexpected number of test errors, XML:\n"
                          f"{xml_output}"))

        n_failures = int(testsuite_tag.attributes['failures'].value)
        self.assertEqual(n_failures, e_nfailures,
                         (f"Unexpected number of test failures, XML:\n"
                          f"{xml_output}"))

        n_skip = int(testsuite_tag.attributes['skipped'].value)
        self.assertEqual(n_skip, e_nskip,
                         f"Unexpected number of test skips, XML:\n"
                         f"{xml_output}")

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
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo --json - '
                    f'--archive {testname}')
        result = process.run(cmd_line, ignore_status=True)
        json_output = result.stdout_text
        self.assertEqual(result.exit_status, e_rc,
                         f"Avocado did not return rc {e_rc}:\n{result}")
        try:
            json_data = json.loads(json_output)
        except Exception as detail:
            raise ParseJSONError((f"Failed to parse content: {detail}\n"
                                  f"{json_output}"))
        self.assertTrue(json_data, f"Empty JSON result:\n{json_output}")
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
