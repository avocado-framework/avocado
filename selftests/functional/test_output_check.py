import json
import os
import unittest

from avocado.core import exit_codes
from avocado.utils import process, script
from selftests.utils import AVOCADO, TestCaseTmpDir

STDOUT = b"Hello, \xc4\x9b\xc5\xa1\xc4\x8d\xc5\x99\xc5\xbe\xc3\xbd\xc3\xa1\xc3\xad\xc3\xa9!\n"
STDERR = b"Hello, stderr!\n"

JSON_VARIANTS = """
[{"paths": ["/run/*"],
 "variant": [["/run/params/foo",
            [["/run/params/foo", "p2", "foo2"],
             ["/run/params/foo", "p1", "foo1"]]]],
 "variant_id": "foo"},
{"paths": ["/run/*"],
 "variant": [["/run/params/bar",
            [["/run/params/bar", "p2", "bar2"],
             ["/run/params/bar", "p1", "bar1"]]]],
 "variant_id": "bar"}]
 """

TEST_WITH_SAME_EXPECTED_OUTPUT = """
from avocado import Test
import logging


class PassTest(Test):

    def test_1(self):

        stdout = logging.getLogger('avocado.test.stdout')
        stdout.info('Informational line that will go to stdout')
        stderr = logging.getLogger('avocado.test.stderr')
        stderr.info('Informational line that will go to stderr')

    def test_2(self):

        stdout = logging.getLogger('avocado.test.stdout')
        stdout.info('Informational line that will go to stdout')
        stderr = logging.getLogger('avocado.test.stderr')
        stderr.info('Informational line that will go to stderr')
"""

TEST_WITH_DIFFERENT_EXPECTED_OUTPUT = """
from avocado import Test
import logging


class PassTest(Test):

    def test_1(self):

        stdout = logging.getLogger('avocado.test.stdout')
        stdout.info('Informational line that will go to stdout_1')
        stderr = logging.getLogger('avocado.test.stderr')
        stderr.info('Informational line that will go to stderr_1')

    def test_2(self):

        stdout = logging.getLogger('avocado.test.stdout')
        stdout.info('Informational line that will go to stdout_2')
        stderr = logging.getLogger('avocado.test.stderr')
        stderr.info('Informational line that will go to stderr_2')
"""

TEST_WITH_DIFFERENT_EXPECTED_OUTPUT_VARIANTS = """
from avocado import Test
import logging


class PassTest(Test):

    def test_1(self):
        foo = self.params.get("p1")
        stdout = logging.getLogger('avocado.test.stdout')
        stdout.info('Informational line that will go to stdout_1 %s'%foo)
        stderr = logging.getLogger('avocado.test.stderr')
        stderr.info('Informational line that will go to stderr_1 %s'%foo)
        print("foo %s" %foo)

    def test_2(self):
        bar = self.params.get("p2")
        stdout = logging.getLogger('avocado.test.stdout')
        stdout.info('Informational line that will go to stdout_2 %s'%bar)
        stderr = logging.getLogger('avocado.test.stderr')
        stderr.info('Informational line that will go to stderr_2 %s'%bar)
        print("bar %s" %bar)
"""

TEST_WITH_DIFFERENT_AND_SAME_EXPECTED_OUTPUT = """
from avocado import Test
import logging


class PassTest(Test):

    def test_1(self):

        stdout = logging.getLogger('avocado.test.stdout')
        stdout.info('Informational line that will go to stdout_1')
        stderr = logging.getLogger('avocado.test.stderr')
        stderr.info('Informational line that will go to stderr_1')

    def test_2(self):

        stdout = logging.getLogger('avocado.test.stdout')
        stdout.info('Informational line that will go to stdout_2')
        stderr = logging.getLogger('avocado.test.stderr')
        stderr.info('Informational line that will go to stderr_2')

    def test_3(self):

        stdout = logging.getLogger('avocado.test.stdout')
        stdout.info('Informational line that will go to stdout_2')
        stderr = logging.getLogger('avocado.test.stderr')
        stderr.info('Informational line that will go to stderr_2')
"""


@unittest.skip('Skipping until output-check-record feature will be in nrunner #3882.')
class RunnerSimpleTest(TestCaseTmpDir):

    def assertIsFile(self, path):
        self.assertTrue(os.path.isfile(path))

    def assertIsNotFile(self, path):
        self.assertFalse(os.path.isfile(path))

    def setUp(self):
        super().setUp()
        content = b"#!/bin/sh\necho -n '%s';echo -n '%s'>&2" % (STDOUT, STDERR)
        self.output_script = script.TemporaryScript(
            'output_check.sh',
            content,
            'avocado_output_check_functional',
            open_mode='wb')  # pylint: disable=W1514
        self.output_script.save()

    def _check_output_record_all(self):
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {self.output_script.path} '
                    f'--output-check-record all')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        stdout_file = f"{self.output_script}.data/stdout.expected"
        stderr_file = f"{self.output_script}.data/stderr.expected"
        with open(stdout_file, 'rb') as fd_stdout:  # pylint: disable=W1514
            self.assertEqual(fd_stdout.read(), STDOUT)
        with open(stderr_file, 'rb') as fd_stderr:  # pylint: disable=W1514
            self.assertEqual(fd_stderr.read(), STDERR)

    def _check_output_record_combined(self):
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {self.output_script.path} '
                    f'--output-check-record combined')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        output_file = f"{self.output_script}.data/output.expected"
        with open(output_file, 'rb') as fd_output:  # pylint: disable=W1514
            self.assertEqual(fd_output.read(), STDOUT + STDERR)

    def _setup_simple_test(self, simple_test_content):
        variants_file = os.path.join(self.tmpdir.name, 'variants.json')
        with open(variants_file, 'w',  encoding='utf-8') as file_obj:
            file_obj.write(JSON_VARIANTS)
        simple_test = os.path.join(self.tmpdir.name, 'simpletest.py')
        with open(simple_test, 'w', encoding='utf-8') as file_obj:
            file_obj.write(simple_test_content)
        return (simple_test, variants_file)

    def test_output_record_none(self):
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {self.output_script.path} '
                    f'--output-check-record none')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertIsNotFile(f"{self.output_script}.data/stdout.expected")
        self.assertIsNotFile(f"{self.output_script}.data/stderr.expected")

    def test_output_record_stdout(self):
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {self.output_script.path} '
                    f'--output-check-record stdout')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        stdout_file = f"{self.output_script}.data/stdout.expected"
        stderr_file = f"{self.output_script}.data/stderr.expected"
        with open(stdout_file, 'rb') as fd_stdout:  # pylint: disable=W1514
            self.assertEqual(fd_stdout.read(), STDOUT)
        self.assertIsNotFile(stderr_file)

    def test_output_record_and_check(self):
        self._check_output_record_all()
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {self.output_script.path}')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

    def test_output_record_and_check_combined(self):
        self._check_output_record_combined()
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {self.output_script.path}')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

    def test_output_tamper_stdout(self):
        self._check_output_record_all()
        tampered_msg = b"I PITY THE FOOL THAT STANDS ON MY WAY!"
        stdout_file = f"{self.output_script.path}.data/stdout.expected"
        with open(stdout_file, 'wb') as stdout_file_obj:  # pylint: disable=W1514
            stdout_file_obj.write(tampered_msg)
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {self.output_script.path} --xunit -')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertIn(tampered_msg, result.stdout)

    def test_output_tamper_combined(self):
        self._check_output_record_combined()
        tampered_msg = b"I PITY THE FOOL THAT STANDS ON MY WAY!"
        output_file = f"{self.output_script.path}.data/output.expected"
        with open(output_file, 'wb') as output_file_obj:  # pylint: disable=W1514
            output_file_obj.write(tampered_msg)
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {self.output_script.path} --xunit -')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertIn(tampered_msg, result.stdout)

    def test_output_diff(self):
        self._check_output_record_all()
        tampered_msg_stdout = b"I PITY THE FOOL THAT STANDS ON STDOUT!"
        tampered_msg_stderr = b"I PITY THE FOOL THAT STANDS ON STDERR!"

        stdout_file = f"{self.output_script.path}.data/stdout.expected"
        with open(stdout_file, 'wb') as stdout_file_obj:  # pylint: disable=W1514
            stdout_file_obj.write(tampered_msg_stdout)

        stderr_file = f"{self.output_script.path}.data/stderr.expected"
        with open(stderr_file, 'wb') as stderr_file_obj:  # pylint: disable=W1514
            stderr_file_obj.write(tampered_msg_stderr)

        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {self.output_script.path} --json -')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

        json_result = json.loads(result.stdout_text)
        job_log = json_result['debuglog']
        stdout_diff = os.path.join(json_result['tests'][0]['logdir'],
                                   'stdout.diff')
        stderr_diff = os.path.join(json_result['tests'][0]['logdir'],
                                   'stderr.diff')

        with open(stdout_diff, 'rb') as stdout_diff_obj:  # pylint: disable=W1514
            stdout_diff_content = stdout_diff_obj.read()
        self.assertIn(b'-I PITY THE FOOL THAT STANDS ON STDOUT!',
                      stdout_diff_content)
        self.assertIn(b'+' + STDOUT, stdout_diff_content)

        with open(stderr_diff, 'rb') as stderr_diff_obj:  # pylint: disable=W1514
            stderr_diff_content = stderr_diff_obj.read()
        self.assertIn(b'-I PITY THE FOOL THAT STANDS ON STDERR!',
                      stderr_diff_content)
        self.assertIn(b'+Hello, stderr!', stderr_diff_content)

        with open(job_log, 'rb') as job_log_obj:  # pylint: disable=W1514
            job_log_content = job_log_obj.read()
        self.assertIn(b'Stdout Diff:', job_log_content)
        self.assertIn(b'-I PITY THE FOOL THAT STANDS ON STDOUT!', job_log_content)
        self.assertIn(b'+' + STDOUT, job_log_content)
        self.assertIn(b'Stdout Diff:', job_log_content)
        self.assertIn(b'-I PITY THE FOOL THAT STANDS ON STDERR!', job_log_content)
        self.assertIn(b'+' + STDERR, job_log_content)

    def test_disable_output_check(self):
        self._check_output_record_all()
        tampered_msg = b"I PITY THE FOOL THAT STANDS ON MY WAY!"
        stdout_file = f"{self.output_script.path}.data/stdout.expected"
        with open(stdout_file, 'wb') as stdout_file_obj:  # pylint: disable=W1514
            stdout_file_obj.write(tampered_msg)
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {self.output_script.path} '
                    f'--disable-output-check --xunit -')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertNotIn(tampered_msg, result.stdout)

    def test_merge_records_same_output(self):
        variants_file = os.path.join(self.tmpdir.name, 'variants.json')
        with open(variants_file, 'w', encoding='utf-8') as file_obj:
            file_obj.write(JSON_VARIANTS)
        simple_test = os.path.join(self.tmpdir.name, 'simpletest.py')
        with open(simple_test, 'w', encoding='utf-8') as file_obj:
            file_obj.write(TEST_WITH_SAME_EXPECTED_OUTPUT)
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {simple_test} --output-check-record '
                    f'both --json-variants-load {variants_file}')
        process.run(cmd_line, ignore_status=True)
        self.assertIsFile(f"{simple_test}.data/stdout.expected")
        self.assertIsFile(f"{simple_test}.data/stderr.expected")

    def test_merge_records_different_output(self):
        simple_test, variants_file = self._setup_simple_test(
            TEST_WITH_DIFFERENT_EXPECTED_OUTPUT)
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {simple_test} '
                    f'--output-check-record both '
                    f'--json-variants-load {variants_file}')
        process.run(cmd_line, ignore_status=True)
        self.assertIsNotFile(f"{simple_test}.data/stdout.expected")
        self.assertIsNotFile(f"{simple_test}.data/stderr.expected")
        self.assertIsFile(f"{simple_test}.data/PassTest.test_1/stdout.expected")
        self.assertIsFile(f"{simple_test}.data/PassTest.test_1/stderr.expected")
        self.assertIsFile(f"{simple_test}.data/PassTest.test_2/stdout.expected")
        self.assertIsFile(f"{simple_test}.data/PassTest.test_2/stderr.expected")

    def test_merge_records_different_output_variants(self):
        simple_test, variants_file = self._setup_simple_test(
            TEST_WITH_DIFFERENT_EXPECTED_OUTPUT_VARIANTS)
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {simple_test} --output-check-record both '
                    f'--json-variants-load {variants_file}')
        process.run(cmd_line, ignore_status=True)
        self.assertIsNotFile(f"{simple_test}.data/stdout.expected")
        self.assertIsNotFile(f"{simple_test}.data/stderr.expected")
        self.assertIsNotFile(f"{simple_test}.data/PassTest.test_1/stdout.expected")
        self.assertIsNotFile(f"{simple_test}.data/PassTest.test_1/stderr.expected")
        self.assertIsNotFile(f"{simple_test}.data/PassTest.test_2/stdout.expected")
        self.assertIsNotFile(f"{simple_test}.data/PassTest.test_2/stderr.expected")
        self.assertIsFile(f"{simple_test}.data/PassTest.test_2/bar/stderr.expected")
        self.assertIsFile(f"{simple_test}.data/PassTest.test_2/foo/stderr.expected")

    def test_merge_records_different_and_same_output(self):
        simple_test, variants_file = self._setup_simple_test(
            TEST_WITH_DIFFERENT_AND_SAME_EXPECTED_OUTPUT)
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo {simple_test} --output-check-record both '
                    f'--json-variants-load {variants_file}')
        process.run(cmd_line, ignore_status=True)
        self.assertIsFile(f"{simple_test}.data/stdout.expected")
        self.assertIsFile(f"{simple_test}.data/stderr.expected")
        self.assertIsFile(f"{simple_test}.data/PassTest.test_1/stdout.expected")
        self.assertIsFile(f"{simple_test}.data/PassTest.test_1/stderr.expected")
        self.assertIsNotFile(f"{simple_test}.data/PassTest.test_2/stdout.expected")
        self.assertIsNotFile(f"{simple_test}.data/PassTest.test_2/stderr.expected")

    def tearDown(self):
        super().tearDown()
        self.output_script.remove()


if __name__ == '__main__':
    unittest.main()
