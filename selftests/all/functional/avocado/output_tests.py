import json
import tempfile
import unittest
import os
import sys
import shutil
from xml.dom import minidom

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import process
from avocado.core.output import TermSupport


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
        cmd_line = './scripts/avocado run --xunit - --json - passtest'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 2
        output = result.stdout + result.stderr
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        error_excerpt = "Options --json --xunit are trying to use stdout simultaneously"
        self.assertIn(error_excerpt, output,
                      "Missing excerpt error message from output:\n%s" % output)

    def test_output_incompatible_setup_2(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --vm --json - passtest'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 2
        output = result.stdout + result.stderr
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        error_excerpt = "Options --json --vm are trying to use stdout simultaneously"
        self.assertIn(error_excerpt, output,
                      "Missing excerpt error message from output:\n%s" % output)

    def test_output_incompatible_setup_3(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --html - sleeptest'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 2
        output = result.stdout + result.stderr
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        error_excerpt = "HTML to stdout not supported"
        self.assertIn(error_excerpt, output,
                      "Missing excerpt error message from output:\n%s" % output)

    def test_output_compatible_setup(self):
        tmpfile = tempfile.mktemp()
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --journal --xunit %s --json - passtest' % tmpfile
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
        cmd_line = './scripts/avocado run --xunit - --json %s passtest' % tmpfile
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

    def test_output_compatible_setup_3(self):
        tmpfile = tempfile.mktemp()
        tmpfile2 = tempfile.mktemp()
        tmpdir = tempfile.mkdtemp()
        tmpfile3 = tempfile.mktemp(dir=tmpdir)
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --xunit %s --json %s --html %s passtest' %
                    (tmpfile, tmpfile2, tmpfile3))
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = 0
        tmpdir_contents = os.listdir(tmpdir)
        self.assertEqual(len(tmpdir_contents), 5,
                         'Not all resources dir were created: %s' % tmpdir_contents)
        try:
            self.assertEqual(result.exit_status, expected_rc,
                             "Avocado did not return rc %d:\n%s" %
                             (expected_rc, result))
            self.assertNotEqual(output, "", "Output is empty")
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
                shutil.rmtree(tmpdir)
            except OSError:
                pass

    def test_output_compatible_setup_nooutput(self):
        tmpfile = tempfile.mktemp()
        tmpfile2 = tempfile.mktemp()
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --silent --xunit %s --json %s passtest' % (tmpfile, tmpfile2)
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = 0
        try:
            self.assertEqual(result.exit_status, expected_rc,
                             "Avocado did not return rc %d:\n%s" %
                             (expected_rc, result))
            self.assertEqual(output, "", "Output is not empty:\n%s" % output)
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

    def test_show_job_log(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run passtest --show-job-log'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def test_silent_trumps_show_job_log(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run passtest --show-job-log --silent'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertEqual(output, "")

    def test_default_enabled_plugins(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run passtest'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        output_lines = output.splitlines()
        second_line = output_lines[1]
        debug_log = second_line.split()[-1]
        self.check_output_files(debug_log)

    def test_verify_whiteboard_save(self):
        tmpfile = tempfile.mktemp()
        try:
            os.chdir(basedir)
            cmd_line = './scripts/avocado run whiteboard --json %s' % tmpfile
            result = process.run(cmd_line, ignore_status=True)
            expected_rc = 0
            self.assertEqual(result.exit_status, expected_rc,
                             "Avocado did not return rc %d:\n%s" %
                             (expected_rc, result))
            with open(tmpfile, 'r') as fp:
                json_results = json.load(fp)
                debug_log = json_results['debuglog']
                debug_dir = os.path.dirname(debug_log)
                test_result_dir = os.path.join(debug_dir, 'test-results', 'whiteboard.py')
                whiteboard_path = os.path.join(test_result_dir, 'whiteboard')
                self.assertTrue(os.path.exists(whiteboard_path),
                                'Missing whiteboard file %s' % whiteboard_path)
        finally:
            try:
                os.remove(tmpfile)
            except OSError:
                pass

    def test_redirect_output(self):
        redirected_output_path = tempfile.mktemp()
        try:
            os.chdir(basedir)
            cmd_line = './scripts/avocado run passtest > %s' % redirected_output_path
            result = process.run(cmd_line, ignore_status=True, shell=True)
            output = result.stdout + result.stderr
            expected_rc = 0
            self.assertEqual(result.exit_status, expected_rc,
                             "Avocado did not return rc %d:\n%s" %
                             (expected_rc, result))
            assert output == '', 'After redirecting to file, output is not empty: %s' % output
            with open(redirected_output_path, 'r') as redirected_output_file_obj:
                redirected_output = redirected_output_file_obj.read()
                for code in TermSupport.ESCAPE_CODES:
                    self.assertNotIn(code,  redirected_output,
                                     'Found terminal support code %s in redirected output\n%s' %
                                     (code, redirected_output))
        finally:
            try:
                os.remove(redirected_output_path)
            except OSError:
                pass


if __name__ == '__main__':
    unittest.main()
