import json
import tempfile
import os
import re
import sys
import shutil
from xml.dom import minidom

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import exit_codes
from avocado.core.output import TermSupport
from avocado.utils import process

basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


def image_output_uncapable():
    try:
        import PIL
        return False
    except ImportError:
        return True


class OutputTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def test_output_doublefree(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    'doublefree.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        output = result.stdout + result.stderr
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        bad_string = 'double free or corruption'
        self.assertNotIn(bad_string, output,
                         "Libc double free can be seen in avocado "
                         "doublefree output:\n%s" % output)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class OutputPluginTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def check_output_files(self, debug_log):
        base_dir = os.path.dirname(debug_log)
        json_output = os.path.join(base_dir, 'results.json')
        self.assertTrue(os.path.isfile(json_output))
        with open(json_output, 'r') as fp:
            json.load(fp)
        xunit_output = os.path.join(base_dir, 'results.xml')
        self.assertTrue(os.path.isfile(json_output))
        try:
            minidom.parse(xunit_output)
        except Exception, details:
            raise AssertionError("Unable to parse xunit output: %s\n\n%s"
                                 % (details, open(xunit_output).read()))

    def test_output_incompatible_setup(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--xunit - --json - passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        output = result.stdout + result.stderr
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        error_regex = re.compile(r'Options ((--json --xunit)|(--xunit --json)) '
                                 'are trying to use stdout simultaneously')
        self.assertIsNotNone(error_regex.match(output),
                             "Missing error message from output:\n%s" % output)

    def test_output_incompatible_setup_2(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--html - passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
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
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--journal --xunit %s --json - passtest.py' %
                    (self.tmpdir, tmpfile))
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = exit_codes.AVOCADO_ALL_OK
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
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--xunit - --json %s passtest.py' %
                    (self.tmpdir, tmpfile))
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = exit_codes.AVOCADO_ALL_OK
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
        tmpfile = tempfile.mktemp(prefix='avocado_' + __name__)
        tmpfile2 = tempfile.mktemp(prefix='avocado_' + __name__)
        tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        tmpfile3 = tempfile.mktemp(dir=tmpdir)
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--xunit %s --json %s --html %s passtest.py' %
                    (self.tmpdir, tmpfile, tmpfile2, tmpfile3))
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = exit_codes.AVOCADO_ALL_OK
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
        # Verify --silent can be supplied as app argument
        cmd_line = ('./scripts/avocado --silent run --job-results-dir %s '
                    '--sysinfo=off --xunit %s --json %s passtest.py' %
                    (self.tmpdir, tmpfile, tmpfile2))
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = exit_codes.AVOCADO_ALL_OK
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

    def test_nonprintable_chars(self):
        cmd_line = ("./scripts/avocado run '/bin/ls "
                    "NON_EXISTING_FILE_WITH_NONPRINTABLE_CHARS_IN_HERE\x1b' "
                    "--job-results-dir %s --sysinfo=off" % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        debug_log = None
        for line in output.splitlines():
            if "JOB LOG" in line:
                debug_log = line.split(':', 1)[-1].strip()
                break
        self.assertTrue(debug_log, "Unable to get JOB LOG from output:\n%s"
                        % output)
        self.check_output_files(debug_log)

    def test_show_job_log(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    'passtest.py --show-job-log' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        job_id_list = re.findall('Job ID: (.*)', result.stdout,
                                 re.MULTILINE)
        self.assertTrue(job_id_list, 'No Job ID in stdout:\n%s' %
                        result.stdout)
        job_id = job_id_list[0]
        self.assertEqual(len(job_id), 40)

    def test_silent_trumps_show_job_log(self):
        os.chdir(basedir)
        # Also verify --silent can be supplied as run option
        cmd_line = ('./scripts/avocado run --silent --job-results-dir %s '
                    '--sysinfo=off passtest.py --show-job-log' %
                    self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertEqual(output, "")

    def test_default_enabled_plugins(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    'passtest.py' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        output_lines = output.splitlines()
        # The current human output produces 6 lines when running a single test,
        # with an optional 7th line when the HTML report generation is enabled
        self.assertGreaterEqual(len(output_lines), 6,
                                ('Basic human interface did not produce the '
                                 'expect output. Output produced: "%s"' % output))
        second_line = output_lines[1]
        debug_log = second_line.split()[-1]
        self.check_output_files(debug_log)

    def test_verify_whiteboard_save(self):
        tmpfile = tempfile.mktemp()
        try:
            os.chdir(basedir)
            cmd_line = ('./scripts/avocado run --job-results-dir %s '
                        '--sysinfo=off whiteboard.py --json %s' %
                        (self.tmpdir, tmpfile))
            result = process.run(cmd_line, ignore_status=True)
            expected_rc = exit_codes.AVOCADO_ALL_OK
            self.assertEqual(result.exit_status, expected_rc,
                             "Avocado did not return rc %d:\n%s" %
                             (expected_rc, result))
            with open(tmpfile, 'r') as fp:
                json_results = json.load(fp)
                logfile = json_results['tests'][0]['logfile']
                debug_dir = os.path.dirname(logfile)
                whiteboard_path = os.path.join(debug_dir, 'whiteboard')
                self.assertTrue(os.path.exists(whiteboard_path),
                                'Missing whiteboard file %s' % whiteboard_path)
        finally:
            try:
                os.remove(tmpfile)
            except OSError:
                pass

    @unittest.skipIf(image_output_uncapable(),
                     "Uncapable of generating images with PIL library")
    def test_gendata(self):
        tmpfile = tempfile.mktemp()
        try:
            os.chdir(basedir)
            cmd_line = ("./scripts/avocado run --job-results-dir %s "
                        "--sysinfo=off gendata.py --json %s" %
                        (self.tmpdir, tmpfile))
            result = process.run(cmd_line, ignore_status=True)
            expected_rc = exit_codes.AVOCADO_ALL_OK
            self.assertEqual(result.exit_status, expected_rc,
                             "Avocado did not return rc %d:\n%s" %
                             (expected_rc, result))
            with open(tmpfile, 'r') as fp:
                json_results = json.load(fp)
                bsod_dir = None
                json_dir = None
                for test in json_results['tests']:
                    if "test_bsod" in test['url']:
                        bsod_dir = test['logfile']
                    elif "test_json" in test['url']:
                        json_dir = test['logfile']
                self.assertTrue(bsod_dir, "Failed to get test_bsod output "
                                "directory")
                self.assertTrue(json_dir, "Failed to get test_json output "
                                "directory")
                bsod_dir = os.path.join(os.path.dirname(bsod_dir), "data",
                                        "bsod.png")
                json_dir = os.path.join(os.path.dirname(json_dir), "data",
                                        "test.json")
                self.assertTrue(os.path.exists(bsod_dir), "File %s produced by"
                                "test does not exist" % bsod_dir)
                self.assertTrue(os.path.exists(json_dir), "File %s produced by"
                                "test does not exist" % json_dir)
        finally:
            try:
                os.remove(tmpfile)
            except OSError:
                pass

    def test_redirect_output(self):
        redirected_output_path = tempfile.mktemp()
        try:
            os.chdir(basedir)
            cmd_line = ('./scripts/avocado run --job-results-dir %s '
                        '--sysinfo=off passtest.py > %s' %
                        (self.tmpdir, redirected_output_path))
            result = process.run(cmd_line, ignore_status=True, shell=True)
            output = result.stdout + result.stderr
            expected_rc = exit_codes.AVOCADO_ALL_OK
            self.assertEqual(result.exit_status, expected_rc,
                             "Avocado did not return rc %d:\n%s" %
                             (expected_rc, result))
            self.assertEqual(output, '',
                             'After redirecting to file, output is not empty: %s' % output)
            with open(redirected_output_path, 'r') as redirected_output_file_obj:
                redirected_output = redirected_output_file_obj.read()
                for code in TermSupport.ESCAPE_CODES:
                    self.assertNotIn(code, redirected_output,
                                     'Found terminal support code %s in redirected output\n%s' %
                                     (code, redirected_output))
        finally:
            try:
                os.remove(redirected_output_path)
            except OSError:
                pass

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
