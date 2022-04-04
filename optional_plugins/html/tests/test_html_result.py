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
        html_output = f"{self.tmpdir.name}/output.html"
        cmd_line = (f'{AVOCADO} run --html {html_output} '
                    f'--job-results-dir {self.tmpdir.name} '
                    f'examples/tests/passtest.py')
        result = process.run(cmd_line)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         (f'Avocado did not return rc '
                          f'{int(expected_rc)}:\n{result}'))
        with open(html_output, 'rt', encoding='utf-8') as fp:
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
        with open(json_output_path, 'r', encoding='utf-8') as fp:
            json.load(fp)
        xunit_output_path = os.path.join(base_dir, 'results.xml')
        self.assertTrue(os.path.isfile(json_output_path))
        try:
            minidom.parse(xunit_output_path)
        except Exception as details:
            xunit_output_content = genio.read_file(xunit_output_path)
            raise AssertionError(f"Unable to parse xunit output: "
                                 f"{details}\n\n{xunit_output_content}")
        tap_output = os.path.join(base_dir, "results.tap")
        self.assertTrue(os.path.isfile(tap_output))
        tap = genio.read_file(tap_output)
        self.assertIn("..", tap)
        self.assertIn("\n# debug.log of ", tap)

    def test_output_incompatible_setup(self):
        cmd_line = (f'avocado run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo '
                    f'--html - passtest.py')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        output = result.stdout + result.stderr
        self.assertEqual(result.exit_status, expected_rc,
                         (f'Avocado did not return rc '
                          f'{int(expected_rc)}:\n{result}'))
        error_excerpt = b"HTML to stdout not supported"
        self.assertIn(error_excerpt, output,
                      f"Missing excerpt error message from output:\n{output}")

    def test_output_compatible_setup_2(self):
        prefix = 'avocado_' + __name__
        tmpfile = tempfile.mktemp(prefix=prefix, dir=self.tmpdir.name)
        tmpfile2 = tempfile.mktemp(prefix=prefix, dir=self.tmpdir.name)
        tmpdir = tempfile.mkdtemp(prefix=prefix, dir=self.tmpdir.name)
        tmpfile3 = os.path.join(tmpdir, "result.html")
        cmd_line = (f'avocado run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo --xunit {tmpfile} --json {tmpfile2} '
                    f'--html {tmpfile3} --tap-include-logs '
                    f'examples/tests/passtest.py')
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = exit_codes.AVOCADO_ALL_OK
        tmpdir_contents = os.listdir(tmpdir)
        self.assertEqual(len(tmpdir_contents), 1,
                         f"Html plugin generated "
                         f"extra files in the result dir: {tmpdir_contents}")
        self.assertEqual(result.exit_status, expected_rc,
                         (f'Avocado did not return rc '
                          f'{int(expected_rc)}:\n{result}'))
        self.assertNotEqual(output, "", "Output is empty")
        # Check if we are producing valid outputs
        with open(tmpfile2, 'r', encoding='utf-8') as fp:
            json_results = json.load(fp)
            debug_log = json_results['debuglog']
            self.check_output_files(debug_log)
        minidom.parse(tmpfile)

    def tearDown(self):
        self.tmpdir.cleanup()
