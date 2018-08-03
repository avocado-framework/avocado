import json
import os
import shutil
import tempfile
import unittest

from avocado.core import exit_codes
from avocado.utils import process
from avocado.utils import script

from .. import AVOCADO, BASEDIR


STDOUT = b"Hello, \xc4\x9b\xc5\xa1\xc4\x8d\xc5\x99\xc5\xbe\xc3\xbd\xc3\xa1\xc3\xad\xc3\xa9!"
STDERR = b"Hello, stderr!"


class RunnerSimpleTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        content = b"#!/bin/sh\n"
        content += b"echo \"" + STDOUT + b"\"\n"
        content += b"echo \"" + STDERR + b"\" >&2\n"
        self.output_script = script.TemporaryScript(
            'output_check.sh',
            content,
            'avocado_output_check_functional',
            open_mode='wb')
        self.output_script.save()

    def _check_output_record_all(self):
        os.chdir(BASEDIR)
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off %s '
                    '--output-check-record all'
                    % (AVOCADO, self.tmpdir, self.output_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        stdout_file = os.path.join("%s.data/stdout.expected" % self.output_script)
        stderr_file = os.path.join("%s.data/stderr.expected" % self.output_script)
        with open(stdout_file, 'rb') as fd_stdout:
            self.assertEqual(fd_stdout.read(), STDOUT)
        with open(stderr_file, 'rb') as fd_stderr:
            self.assertEqual(fd_stderr.read(), STDERR)

    def _check_output_record_combined(self):
        os.chdir(BASEDIR)
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off %s '
                    '--output-check-record combined'
                    % (AVOCADO, self.tmpdir, self.output_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        output_file = os.path.join("%s.data/output.expected" % self.output_script)
        with open(output_file, 'rb') as fd_output:
            self.assertEqual(fd_output.read(), STDOUT + STDERR)

    def test_output_record_none(self):
        os.chdir(BASEDIR)
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off %s '
                    '--output-check-record none'
                    % (AVOCADO, self.tmpdir, self.output_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        stdout_file = os.path.join("%s.data/stdout.expected" % self.output_script)
        stderr_file = os.path.join("%s.data/stderr.expected" % self.output_script)
        self.assertFalse(os.path.isfile(stdout_file))
        self.assertFalse(os.path.isfile(stderr_file))

    def test_output_record_stdout(self):
        os.chdir(BASEDIR)
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off %s '
                    '--output-check-record stdout'
                    % (AVOCADO, self.tmpdir, self.output_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        stdout_file = os.path.join("%s.data/stdout.expected" % self.output_script)
        stderr_file = os.path.join("%s.data/stderr.expected" % self.output_script)
        with open(stdout_file, 'rb') as fd_stdout:
            self.assertEqual(fd_stdout.read(), STDOUT)
        self.assertFalse(os.path.isfile(stderr_file))

    def test_output_record_and_check(self):
        self._check_output_record_all()
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off %s'
                    % (AVOCADO, self.tmpdir, self.output_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def test_output_record_and_check_combined(self):
        self._check_output_record_combined()
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off %s'
                    % (AVOCADO, self.tmpdir, self.output_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def test_output_tamper_stdout(self):
        self._check_output_record_all()
        tampered_msg = b"I PITY THE FOOL THAT STANDS ON MY WAY!"
        stdout_file = os.path.join("%s.data/stdout.expected" % self.output_script.path)
        with open(stdout_file, 'wb') as stdout_file_obj:
            stdout_file_obj.write(tampered_msg)
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off %s --xunit -'
                    % (AVOCADO, self.tmpdir, self.output_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn(tampered_msg, result.stdout)

    def test_output_tamper_combined(self):
        self._check_output_record_combined()
        tampered_msg = b"I PITY THE FOOL THAT STANDS ON MY WAY!"
        output_file = os.path.join("%s.data/output.expected" % self.output_script.path)
        with open(output_file, 'wb') as output_file_obj:
            output_file_obj.write(tampered_msg)
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off %s --xunit -'
                    % (AVOCADO, self.tmpdir, self.output_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn(tampered_msg, result.stdout)

    def test_output_diff(self):
        self._check_output_record_all()
        tampered_msg_stdout = b"I PITY THE FOOL THAT STANDS ON STDOUT!"
        tampered_msg_stderr = b"I PITY THE FOOL THAT STANDS ON STDERR!"

        stdout_file = "%s.data/stdout.expected" % self.output_script.path
        with open(stdout_file, 'wb') as stdout_file_obj:
            stdout_file_obj.write(tampered_msg_stdout)

        stderr_file = "%s.data/stderr.expected" % self.output_script.path
        with open(stderr_file, 'wb') as stderr_file_obj:
            stderr_file_obj.write(tampered_msg_stderr)

        cmd_line = ('%s run --job-results-dir %s --sysinfo=off %s --json -'
                    % (AVOCADO, self.tmpdir, self.output_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

        json_result = json.loads(result.stdout_text)
        job_log = json_result['debuglog']
        stdout_diff = os.path.join(json_result['tests'][0]['logdir'],
                                   'stdout.diff')
        stderr_diff = os.path.join(json_result['tests'][0]['logdir'],
                                   'stderr.diff')

        with open(stdout_diff, 'rb') as stdout_diff_obj:
            stdout_diff_content = stdout_diff_obj.read()
        self.assertIn(b'-I PITY THE FOOL THAT STANDS ON STDOUT!',
                      stdout_diff_content)
        self.assertIn(b'+' + STDOUT, stdout_diff_content)

        with open(stderr_diff, 'rb') as stderr_diff_obj:
            stderr_diff_content = stderr_diff_obj.read()
        self.assertIn(b'-I PITY THE FOOL THAT STANDS ON STDERR!',
                      stderr_diff_content)
        self.assertIn(b'+Hello, stderr!', stderr_diff_content)

        with open(job_log, 'rb') as job_log_obj:
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
        stdout_file = os.path.join("%s.data/stdout.expected" % self.output_script.path)
        with open(stdout_file, 'wb') as stdout_file_obj:
            stdout_file_obj.write(tampered_msg)
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off %s '
                    '--output-check=off --xunit -'
                    % (AVOCADO, self.tmpdir, self.output_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn(tampered_msg, result.stdout)

    def tearDown(self):
        self.output_script.remove()
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
