import json
import os
import tempfile
import unittest
from xml.dom import minidom

from avocado.core import exit_codes
from avocado.utils import genio, process
from selftests.utils import AVOCADO


class HtmlResultTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix='avocado_' + __name__)

    def test_sysinfo_html_output(self):
        html_output = "{}/output.html".format(self.tmpdir.name)
        cmd_line = ('{} run --html {} --job-results-dir {} '
                    'examples/tests/passtest.py'.format(AVOCADO, html_output,
                                                        self.tmpdir.name))
        result = process.run(cmd_line)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc %d:\n%s' % (expected_rc,
                                                                result))
        with open(html_output, 'rt') as fp:
            output = fp.read()

        # Try to find some strings on HTML
        self.assertNotEqual(output.find('Filesystem'), -1)
        self.assertNotEqual(output.find('MemAvailable'), -1)
        self.assertRegex(output, r'(BOOT_IMAGE|root)\=',
                         '/proc/cmdline content not found')

    def check_output_files(self, debug_log):
        base_dir = os.path.dirname(debug_log)
        json_output_path = os.path.join(base_dir, 'results.json')
        self.assertTrue(os.path.isfile(json_output_path))
        with open(json_output_path, 'r') as fp:
            json.load(fp)
        xunit_output_path = os.path.join(base_dir, 'results.xml')
        self.assertTrue(os.path.isfile(json_output_path))
        try:
            minidom.parse(xunit_output_path)
        except Exception as details:
            xunit_output_content = genio.read_file(xunit_output_path)
            raise AssertionError("Unable to parse xunit output: %s\n\n%s"
                                 % (details, xunit_output_content))
        tap_output = os.path.join(base_dir, "results.tap")
        self.assertTrue(os.path.isfile(tap_output))
        tap = genio.read_file(tap_output)
        self.assertIn("..", tap)
        self.assertIn("\n# debug.log of ", tap)

    def test_output_incompatible_setup(self):
        cmd_line = ('avocado run --job-results-dir %s --disable-sysinfo '
                    '--html - passtest.py' % self.tmpdir.name)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        output = result.stdout + result.stderr
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        error_excerpt = b"HTML to stdout not supported"
        self.assertIn(error_excerpt, output,
                      "Missing excerpt error message from output:\n%s" % output)

    def test_output_compatible_setup_2(self):
        prefix = 'avocado_' + __name__
        tmpfile = tempfile.mktemp(prefix=prefix, dir=self.tmpdir.name)
        tmpfile2 = tempfile.mktemp(prefix=prefix, dir=self.tmpdir.name)
        tmpdir = tempfile.mkdtemp(prefix=prefix, dir=self.tmpdir.name)
        tmpfile3 = os.path.join(tmpdir, "result.html")
        cmd_line = ('avocado run --job-results-dir %s --disable-sysinfo '
                    '--xunit %s --json %s --html %s --tap-include-logs '
                    'examples/tests/passtest.py' % (self.tmpdir.name, tmpfile, tmpfile2, tmpfile3))
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = exit_codes.AVOCADO_ALL_OK
        tmpdir_contents = os.listdir(tmpdir)
        self.assertEqual(len(tmpdir_contents), 1, "Html plugin generated "
                         "extra files in the result dir: %s"
                         % tmpdir_contents)
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

    def tearDown(self):
        self.tmpdir.cleanup()
