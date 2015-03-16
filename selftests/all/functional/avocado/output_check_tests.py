import os
import sys
import unittest

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import process
from avocado.utils import script

OUTPUT_SCRIPT_CONTENTS = """#!/bin/sh
echo "Hello, avocado!"
"""


class RunnerSimpleTest(unittest.TestCase):

    def setUp(self):
        self.output_script = script.TemporaryScript(
            'output_check.sh',
            OUTPUT_SCRIPT_CONTENTS,
            'avocado_output_check_functional')
        self.output_script.save()

    def test_output_record_none(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off %s --output-check-record none' % self.output_script.path
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        stdout_file = os.path.join("%s.data/stdout.expected" % self.output_script)
        stderr_file = os.path.join("%s.data/stderr.expected" % self.output_script)
        self.assertFalse(os.path.isfile(stdout_file))
        self.assertFalse(os.path.isfile(stderr_file))

    def test_output_record_stdout(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off %s --output-check-record stdout' % self.output_script.path
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        stdout_file = os.path.join("%s.data/stdout.expected" % self.output_script)
        stderr_file = os.path.join("%s.data/stderr.expected" % self.output_script)
        self.assertTrue(os.path.isfile(stdout_file))
        self.assertFalse(os.path.isfile(stderr_file))

    def test_output_record_all(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off %s --output-check-record all' % self.output_script.path
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        stdout_file = os.path.join("%s.data/stdout.expected" % self.output_script)
        stderr_file = os.path.join("%s.data/stderr.expected" % self.output_script)
        self.assertTrue(os.path.isfile(stdout_file))
        self.assertTrue(os.path.isfile(stderr_file))

    def test_output_record_and_check(self):
        self.test_output_record_all()
        cmd_line = './scripts/avocado run --sysinfo=off %s' % self.output_script.path
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def test_output_tamper_stdout(self):
        self.test_output_record_all()
        tampered_msg = "I PITY THE FOOL THAT STANDS ON MY WAY!"
        stdout_file = os.path.join("%s.data/stdout.expected" % self.output_script.path)
        with open(stdout_file, 'w') as stdout_file_obj:
            stdout_file_obj.write(tampered_msg)
        cmd_line = './scripts/avocado run --sysinfo=off %s --xunit -' % self.output_script.path
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 1
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
        cmd_line = './scripts/avocado run --sysinfo=off %s --output-check=off --xunit -' % self.output_script.path
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn(tampered_msg, result.stdout)

    def tearDown(self):
        self.output_script.remove()

if __name__ == '__main__':
    unittest.main()
