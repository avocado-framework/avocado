import json
import os
import re
import shutil
import tempfile
import unittest
from xml.dom import minidom

from avocado.core import exit_codes
from avocado.core.output import TermSupport
from avocado.utils import genio
from avocado.utils import process
from avocado.utils import script
from avocado.utils import path as utils_path

from .. import AVOCADO, BASEDIR


# AVOCADO may contain more than a single command, as it can be
# prefixed by the Python interpreter
AVOCADO_QUOTED = ", ".join(["'%s'" % cmd for cmd in AVOCADO.split(' ')])
PERL_TAP_PARSER_SNIPPET = """#!/bin/env perl
use TAP::Parser;

my $parser = TAP::Parser->new( { exec => [%s, 'run', 'passtest.py', 'errortest.py', 'warntest.py', '--tap', '-', '--sysinfo', 'off', '--job-results-dir', '%%s'] } );

while ( my $result = $parser->next ) {
        $result->is_unknown && die "Unknown line \\"" . $result->as_string . "\\" in the TAP output!\n";
}
$parser->parse_errors == 0 || die "Parser errors!\n";
$parser->is_good_plan || die "Plan is not a good plan!\n";
$parser->plan eq '1..3' || die "Plan does not match what was expected!\n";
""" % AVOCADO_QUOTED


OUTPUT_TEST_CONTENT = """#!/bin/env python
import sys

from avocado import Test
from avocado.utils import process

print("top_print")
sys.stdout.write("top_stdout\\n")
sys.stderr.write("top_stderr\\n")
process.run("/bin/echo top_process")

class OutputTest(Test):
    def __init__(self, *args, **kwargs):
        super(OutputTest, self).__init__(*args, **kwargs)
        print("init_print")
        sys.stdout.write("init_stdout\\n")
        sys.stderr.write("init_stderr\\n")
        process.run("/bin/echo init_process")

    def test(self):
        print("test_print")
        sys.stdout.write("test_stdout\\n")
        sys.stderr.write("test_stderr\\n")
        process.run("/bin/echo -n test_process > /dev/stdout",
                    shell=True)
        process.run("/bin/echo -n __test_stderr__ > /dev/stderr",
                    shell=True)
        process.run("/bin/echo -n __test_stdout__ > /dev/stdout",
                    shell=True)

    def __del__(self):
        print("del_print")
        sys.stdout.write("del_stdout\\n")
        sys.stderr.write("del_stderr\\n")
        process.run("/bin/echo -n del_process")
"""

OUTPUT_MODE_NONE_CONTENT = r"""
import sys

from avocado import Test
from avocado.utils import process


class OutputCheckNone(Test):

    def test(self):
        cmd = "%s -c \"import sys; sys.%%s.write('%%s')\"" % sys.executable
        process.run(cmd % ('stdout', '__STDOUT_DONT_RECORD_CONTENT__'))
        process.run(cmd % ('stderr', '__STDERR_DONT_RECORD_CONTENT__'))
"""

OUTPUT_CHECK_ON_OFF_CONTENT = r"""
import sys

from avocado import Test
from avocado.utils import process


class OutputCheckOnOff(Test):

    def test(self):
        cmd = "%s -c \"import sys; sys.%%s.write('%%s')\"" % sys.executable
        # start with the default behavior
        process.run(cmd % ('stdout', '__STDOUT_CONTENT__'))
        process.run(cmd % ('stderr', '__STDERR_CONTENT__'))
        # now shift to no recording
        process.run(cmd % ('stdout', '__STDOUT_DONT_RECORD_CONTENT__'),
                    allow_output_check='none')
        process.run(cmd % ('stderr', '__STDERR_DONT_RECORD_CONTENT__'),
                    allow_output_check='none')
        # now check that the default behavior (recording) is effective
        process.run(cmd % ('stdout', '__STDOUT_DO_RECORD_CONTENT__'))
        process.run(cmd % ('stderr', '__STDERR_DO_RECORD_CONTENT__'))
"""


def image_output_uncapable():
    try:
        import PIL              # pylint: disable=W0611,W0612
        return False
    except ImportError:
        return True


def perl_tap_parser_uncapable():
    return os.system("perl -e 'use TAP::Parser;'") != 0


def missing_binary(binary):
    try:
        utils_path.find_command(binary)
        return False
    except utils_path.CmdNotFoundError:
        return True


class OutputTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        os.chdir(BASEDIR)

    @unittest.skipIf(missing_binary('cc'),
                     "C compiler is required by the underlying doublefree.py test")
    def test_output_doublefree(self):
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off '
                    'doublefree.py' % (AVOCADO, self.tmpdir))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        output = result.stdout + result.stderr
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        bad_string = b'double free or corruption'
        self.assertNotIn(bad_string, output,
                         "Libc double free can be seen in avocado "
                         "doublefree output:\n%s" % output)

    def test_print_to_std(self):
        def _check_output(path, exps, name):
            i = 0
            end = len(exps)
            with open(path, 'rb') as output_file:
                output_file_content = output_file.read()
                output_file.seek(0)
                for line in output_file:
                    if exps[i] in line:
                        i += 1
                        if i == end:
                            break
                exps_text = "\n".join([exp.decode() for exp in exps])
                error_msg = ("Failed to find message in position %s from\n%s\n"
                             "\nin the %s. Either it's missing or in wrong "
                             "order.\n%s" % (i, exps_text, name,
                                             output_file_content))
                self.assertEqual(i, end, error_msg)
        test = script.Script(os.path.join(self.tmpdir, "output_test.py"),
                             OUTPUT_TEST_CONTENT)
        test.save()
        result = process.run("%s run --job-results-dir %s --sysinfo=off "
                             "--json - -- %s" % (AVOCADO, self.tmpdir, test))
        res = json.loads(result.stdout_text)
        joblog = res["debuglog"]
        exps = [b"[stdout] top_print", b"[stdout] top_stdout",
                b"[stderr] top_stderr", b"[stdout] top_process",
                b"[stdout] init_print", b"[stdout] init_stdout",
                b"[stderr] init_stderr", b"[stdout] init_process",
                b"[stdout] test_print", b"[stdout] test_stdout",
                b"[stderr] test_stderr", b"[stdout] test_process"]
        _check_output(joblog, exps, "job.log")
        testdir = res["tests"][0]["logdir"]
        with open(os.path.join(testdir, "stdout"), 'rb') as stdout_file:
            self.assertEqual(b"test_print\ntest_stdout\ntest_process__test_stdout__",
                             stdout_file.read())
        with open(os.path.join(testdir, "stderr"), 'rb') as stderr_file:
            self.assertEqual(b"test_stderr\n__test_stderr__",
                             stderr_file.read())

        # Now run the same test, but with combined output
        # combined output can not keep track of sys.stdout and sys.stdout
        # writes, as they will eventually be out of sync.  In fact,
        # the correct fix is to run the entire test process with redirected
        # stdout and stderr, and *not* play with sys.stdout and sys.stderr.
        # But this change will come later
        result = process.run("%s run --job-results-dir %s --sysinfo=off "
                             "--output-check-record=combined "
                             "--json - -- %s" % (AVOCADO, self.tmpdir, test))
        res = json.loads(result.stdout_text)
        testdir = res["tests"][0]["logdir"]
        with open(os.path.join(testdir, "output")) as output_file:
            self.assertEqual("test_process__test_stderr____test_stdout__",
                             output_file.read())

    def test_check_record_no_module_default(self):
        """
        Checks that the `avocado.utils.process` module won't have a output
        check record mode (`OUTPUT_CHECK_RECORD_MODE`) set by default.

        The reason is that, if this is always set from the command
        line runner, we can't distinguish from a situation where the
        module level configuration should be applied as a fallback to
        the API parameter.  By leaving it unset by default, the command line
        option parameter value `none` will slightly change its behavior,
        meaning that it will explicitly disable output check record when
        asked to do so.
        """
        with script.Script(os.path.join(self.tmpdir, "output_mode_none.py"),
                           OUTPUT_MODE_NONE_CONTENT,
                           script.READ_ONLY_MODE) as test:
            command = ("%s run --job-results-dir %s --sysinfo=off "
                       "--json - --output-check-record none -- %s") % (AVOCADO,
                                                                       self.tmpdir,
                                                                       test.path)
            result = process.run(command)
            res = json.loads(result.stdout_text)
            testdir = res["tests"][0]["logdir"]
            for output_file in ('stdout', 'stderr', 'output'):
                output_file_path = os.path.join(testdir, output_file)
                self.assertTrue(os.path.exists(output_file_path))
                with open(output_file_path, 'r') as output:
                    self.assertEqual(output.read(), '')

    def test_check_on_off(self):
        """
        Checks that output will always be kept, but it will only make into
        the *test* stdout/stderr/output files when it's not explicitly disabled

        This control is defined as an API parameter, `allow_output_check`, so
        it should be possible to enable/disable it on each call.
        """
        with script.Script(os.path.join(self.tmpdir, "test_check_on_off.py"),
                           OUTPUT_CHECK_ON_OFF_CONTENT,
                           script.READ_ONLY_MODE) as test:
            command = ("%s run --job-results-dir %s --sysinfo=off "
                       "--json - -- %s") % (AVOCADO, self.tmpdir, test.path)
            result = process.run(command)
            res = json.loads(result.stdout_text)
            testdir = res["tests"][0]["logdir"]
            stdout_path = os.path.join(testdir, 'stdout')
            self.assertTrue(os.path.exists(stdout_path))
            with open(stdout_path, 'r') as stdout:
                self.assertEqual(stdout.read(),
                                 '__STDOUT_CONTENT____STDOUT_DO_RECORD_CONTENT__')
            stderr_path = os.path.join(testdir, 'stderr')
            self.assertTrue(os.path.exists(stderr_path))
            with open(stderr_path, 'r') as stderr:
                self.assertEqual(stderr.read(),
                                 '__STDERR_CONTENT____STDERR_DO_RECORD_CONTENT__')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class OutputPluginTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        os.chdir(BASEDIR)

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
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off '
                    '--xunit - --json - passtest.py' % (AVOCADO, self.tmpdir))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        error_regex = re.compile(r'avocado run: error: argument ((--json)|'
                                 '(--xunit)): Options ((--xunit --json)|'
                                 '(--json --xunit)) are trying to use stdout '
                                 'simultaneously\n')
        self.assertIsNotNone(error_regex.match(result.stderr_text),
                             "Missing error message from output:\n%s" %
                             result.stderr)

    def test_output_compatible_setup(self):
        tmpfile = tempfile.mktemp(dir=self.tmpdir)
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off '
                    '--journal --xunit %s --json - passtest.py' %
                    (AVOCADO, self.tmpdir, tmpfile))
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout_text + result.stderr_text
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        # Check if we are producing valid outputs
        json.loads(output)
        minidom.parse(tmpfile)

    def test_output_compatible_setup_2(self):
        tmpfile = tempfile.mktemp(dir=self.tmpdir)
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off '
                    '--xunit - --json %s --tap-include-logs passtest.py'
                    % (AVOCADO, self.tmpdir, tmpfile))
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        # Check if we are producing valid outputs
        with open(tmpfile, 'r') as fp:
            json_results = json.load(fp)
            debug_log = json_results['debuglog']
            self.check_output_files(debug_log)
        minidom.parseString(output)

    def test_output_compatible_setup_nooutput(self):
        tmpfile = tempfile.mktemp(dir=self.tmpdir)
        tmpfile2 = tempfile.mktemp(dir=self.tmpdir)
        # Verify --silent can be supplied as app argument
        cmd_line = ('%s --silent run --job-results-dir %s '
                    '--sysinfo=off --xunit %s --json %s --tap-include-logs '
                    'passtest.py' % (AVOCADO, self.tmpdir, tmpfile, tmpfile2))
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertEqual(output, b"", "Output is not empty:\n%s" % output)
        # Check if we are producing valid outputs
        with open(tmpfile2, 'r') as fp:
            json_results = json.load(fp)
            debug_log = json_results['debuglog']
            self.check_output_files(debug_log)
        minidom.parse(tmpfile)

    def test_nonprintable_chars(self):
        cmd_line = ("%s run --external-runner /bin/ls "
                    "'NON_EXISTING_FILE_WITH_NONPRINTABLE_CHARS_IN_HERE\x1b' "
                    "--job-results-dir %s --sysinfo=off --tap-include-logs"
                    % (AVOCADO, self.tmpdir))
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout_text + result.stderr_text
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
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off '
                    'passtest.py --show-job-log' % (AVOCADO, self.tmpdir))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        job_id_list = re.findall('Job ID: (.*)', result.stdout_text,
                                 re.MULTILINE)
        self.assertTrue(job_id_list, 'No Job ID in stdout:\n%s' %
                        result.stdout)
        job_id = job_id_list[0]
        self.assertEqual(len(job_id), 40)

    def test_silent_trumps_show_job_log(self):
        # Also verify --silent can be supplied as run option
        cmd_line = ('%s run --silent --job-results-dir %s '
                    '--sysinfo=off passtest.py --show-job-log'
                    % (AVOCADO, self.tmpdir))
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertEqual(output, b"")

    def test_default_enabled_plugins(self):
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off '
                    '--tap-include-logs passtest.py'
                    % (AVOCADO, self.tmpdir))
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout_text + result.stderr_text
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
        tmpfile = tempfile.mktemp(dir=self.tmpdir)
        config = os.path.join(self.tmpdir, "conf.ini")
        content = ("[datadir.paths]\nlogs_dir = %s"
                   % os.path.relpath(self.tmpdir, "."))
        script.Script(config, content).save()
        cmd_line = ('%s --config %s --show all run '
                    '--sysinfo=off whiteboard.py --json %s'
                    % (AVOCADO, config, tmpfile))
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

    @unittest.skipIf(image_output_uncapable(),
                     "Uncapable of generating images with PIL library")
    def test_gendata(self):
        tmpfile = tempfile.mktemp(dir=self.tmpdir)
        cmd_line = ("%s run --job-results-dir %s "
                    "--sysinfo=off gendata.py --json %s" %
                    (AVOCADO, self.tmpdir, tmpfile))
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
                if "test_bsod" in test['id']:
                    bsod_dir = test['logfile']
                elif "test_json" in test['id']:
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

    def test_redirect_output(self):
        redirected_output_path = tempfile.mktemp(dir=self.tmpdir)
        cmd_line = ('%s run --job-results-dir %s '
                    '--sysinfo=off passtest.py > %s'
                    % (AVOCADO, self.tmpdir, redirected_output_path))
        result = process.run(cmd_line, ignore_status=True, shell=True)
        output = result.stdout + result.stderr
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertEqual(output, b'',
                         'After redirecting to file, output is not empty: %s' % output)
        with open(redirected_output_path, 'r') as redirected_output_file_obj:
            redirected_output = redirected_output_file_obj.read()
            for code in TermSupport.ESCAPE_CODES:
                self.assertNotIn(code, redirected_output,
                                 'Found terminal support code %s in redirected output\n%s' %
                                 (code, redirected_output))

    @unittest.skipIf(perl_tap_parser_uncapable(),
                     "Uncapable of using Perl TAP::Parser library")
    def test_tap_parser(self):
        perl_script = script.TemporaryScript("tap_parser.pl",
                                             PERL_TAP_PARSER_SNIPPET
                                             % self.tmpdir)
        perl_script.save()
        process.run("perl %s" % perl_script)

    def test_tap_totaltests(self):
        cmd_line = ("%s run passtest.py "
                    "-m examples/tests/sleeptest.py.data/sleeptest.yaml "
                    "--job-results-dir %s "
                    "--tap -" % (AVOCADO, self.tmpdir))
        result = process.run(cmd_line)
        expr = b'1..4'
        self.assertIn(expr, result.stdout, "'%s' not found in:\n%s"
                      % (expr, result.stdout))

    def test_broken_pipe(self):
        cmd_line = "(%s run --help | whacky-unknown-command)" % AVOCADO
        result = process.run(cmd_line, shell=True, ignore_status=True,
                             env={"LC_ALL": "C"})
        expected_rc = 127
        self.assertEqual(result.exit_status, expected_rc,
                         ("avocado run to broken pipe did not return "
                          "rc %d:\n%s" % (expected_rc, result)))
        self.assertIn(b"whacky-unknown-command", result.stderr)
        self.assertIn(b"not found", result.stderr)
        self.assertNotIn(b"Avocado crashed", result.stderr)

    def test_results_plugins_no_tests(self):
        cmd_line = ("%s run UNEXISTING --job-results-dir %s"
                    % (AVOCADO, self.tmpdir))
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_JOB_FAIL)

        xunit_results = os.path.join(self.tmpdir, 'latest', 'results.xml')
        self.assertFalse(os.path.exists(xunit_results))

        json_results = os.path.join(self.tmpdir, 'latest', 'results.json')
        self.assertFalse(os.path.exists(json_results))

        tap_results = os.path.join(self.tmpdir, 'latest', 'results.tap')
        self.assertFalse(os.path.exists(tap_results))

        # Check that no UI output was generated
        self.assertNotIn(b"RESULTS    : PASS ", result.stdout)
        self.assertNotIn(b"JOB TIME   :", result.stdout)

        # Check that plugins do not produce errors
        self.assertNotIn(b"Error running method ", result.stderr)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
