import os
import sys
import tempfile
import shutil

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import exit_codes
from avocado.utils import process
from avocado.utils import script


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


OUTPUT_SCRIPT_CONTENTS = """#!/bin/sh
echo "Hello, avocado!"
"""


class RunnerSimpleTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.output_script = script.TemporaryScript(
            'output_check.sh',
            OUTPUT_SCRIPT_CONTENTS,
            'avocado_output_check_functional')
        self.output_script.save()

    def test_output_record_none(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off %s --output-check-record none' %
                    (self.tmpdir, self.output_script.path))
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
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off %s --output-check-record stdout' %
                    (self.tmpdir, self.output_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        stdout_file = os.path.join("%s.data/stdout.expected" % self.output_script)
        stderr_file = os.path.join("%s.data/stderr.expected" % self.output_script)
        self.assertTrue(os.path.isfile(stdout_file))
        self.assertFalse(os.path.isfile(stderr_file))

    def test_output_record_all(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off %s --output-check-record all' %
                    (self.tmpdir, self.output_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        stdout_file = os.path.join("%s.data/stdout.expected" % self.output_script)
        stderr_file = os.path.join("%s.data/stderr.expected" % self.output_script)
        self.assertTrue(os.path.isfile(stdout_file))
        self.assertTrue(os.path.isfile(stderr_file))

    def test_output_record_and_check(self):
        self.test_output_record_all()
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off %s' %
                    (self.tmpdir, self.output_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def test_output_tamper_stdout(self):
        self.test_output_record_all()
        tampered_msg = "I PITY THE FOOL THAT STANDS ON MY WAY!"
        stdout_file = os.path.join("%s.data/stdout.expected" % self.output_script.path)
        with open(stdout_file, 'w') as stdout_file_obj:
            stdout_file_obj.write(tampered_msg)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off %s --xunit -' %
                    (self.tmpdir, self.output_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn(tampered_msg, result.stdout)

    def test_disable_output_check(self):
        self.test_output_record_all()
        tampered_msg = "I PITY THE FOOL THAT STANDS ON MY WAY!"
        stdout_file = os.path.join("%s.data/stdout.expected" % self.output_script.path)
        with open(stdout_file, 'w') as stdout_file_obj:
            stdout_file_obj.write(tampered_msg)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off %s --output-check=off --xunit -' %
                    (self.tmpdir, self.output_script.path))
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
