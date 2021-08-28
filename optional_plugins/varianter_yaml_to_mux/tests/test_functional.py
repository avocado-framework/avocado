import glob
import json
import os
import shutil
import tempfile
import unittest

from avocado.core import exit_codes
from avocado.utils import genio, process
from selftests.utils import AVOCADO, BASEDIR


class MultiplexTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix='avocado_' + __name__)

    def run_and_check(self, cmd_line, expected_rc, tests=None):
        os.chdir(BASEDIR)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        if tests is not None:
            exp = ("PASS %s | ERROR 0 | FAIL %s | SKIP 0 | WARN 0 | "
                   "INTERRUPT 0" % tests)
            self.assertIn(exp, result.stdout_text, "%s not in stdout:\n%s"
                          % (exp, result))
        return result

    def test_mplex_plugin(self):
        cmd_line = ('%s variants -m examples/tests/sleeptest.py.data/'
                    'sleeptest.yaml' % AVOCADO)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)

    def test_mplex_plugin_nonexistent(self):
        cmd_line = '%s variants -m nonexist' % AVOCADO
        expected_rc = exit_codes.AVOCADO_FAIL
        result = self.run_and_check(cmd_line, expected_rc)
        self.assertIn('No such file or directory', result.stderr_text)

    def test_mplex_plugin_using(self):
        cmd_line = ('%s variants -m /:optional_plugins/varianter_yaml_to_mux/'
                    'tests/.data/mux-selftest-using.yaml' % AVOCADO)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        result = self.run_and_check(cmd_line, expected_rc)
        self.assertIn(b' /foo/baz/bar', result.stdout)

    def test_run_mplex_noid(self):
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    '-m examples/tests/sleeptest.py.data/sleeptest.yaml'
                    % (AVOCADO, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        self.run_and_check(cmd_line, expected_rc)

    def test_run_mplex_passtest(self):
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    'examples/tests/passtest.py -m '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml'
                    % (AVOCADO, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc, (4, 0))
        # Also check whether jobdata contains correct parameter paths
        with open(os.path.join(self.tmpdir.name, "latest", "jobdata",
                               "variants.json")) as variants_file:
            variants = variants_file.read()
        self.assertIn('["/run/*"]', variants, "parameter paths stored in "
                      "jobdata does not contains [\"/run/*\"]\n%s" % variants)

    def test_run_mplex_doublepass(self):
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    'examples/tests/passtest.py '
                    'examples/tests/passtest.py -m '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml '
                    '--mux-path /foo/\\* /bar/\\* /baz/\\*'
                    % (AVOCADO, self.tmpdir.name))
        self.run_and_check(cmd_line, exit_codes.AVOCADO_ALL_OK, (8, 0))
        # Also check whether jobdata contains correct parameter paths
        with open(os.path.join(self.tmpdir.name, "latest", "jobdata",
                               "variants.json")) as variants_file:
            variants = variants_file.read()
        exp = '["/foo/*", "/bar/*", "/baz/*"]'
        self.assertIn(exp, variants, "parameter paths stored in jobdata "
                      "does not contains %s\n%s" % (exp, variants))

    def test_run_mplex_failtest(self):
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    'examples/tests/passtest.py '
                    'examples/tests/failtest.py -m '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml'
                    % (AVOCADO, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        result = self.run_and_check(cmd_line, expected_rc, (4, 4))
        self.assertIn(b"(1/8) examples/tests/passtest.py:PassTest.test;run-short-beaf",
                      result.stdout)
        self.assertIn(b"(2/8) examples/tests/passtest.py:PassTest.test;run-medium-5595",
                      result.stdout)
        self.assertIn(b"(8/8) examples/tests/failtest.py:FailTest.test;run-longest-efc4",
                      result.stdout)

    def test_run_mplex_failtest_tests_per_variant(self):
        cmd_line = ("%s run --job-results-dir %s --disable-sysinfo "
                    "examples/tests/passtest.py "
                    "examples/tests/failtest.py -m "
                    "examples/tests/sleeptest.py.data/sleeptest.yaml "
                    "--execution-order tests-per-variant"
                    % (AVOCADO, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        result = self.run_and_check(cmd_line, expected_rc, (4, 4))
        self.assertIn(b"(1/8) examples/tests/passtest.py:PassTest.test;run-short-beaf",
                      result.stdout)
        self.assertIn(b"(2/8) examples/tests/failtest.py:FailTest.test;run-short-beaf",
                      result.stdout)
        self.assertIn(b"(8/8) examples/tests/failtest.py:FailTest.test;run-longest-efc4",
                      result.stdout)

    def test_run_double_mplex(self):
        cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                    'examples/tests/passtest.py -m '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml'
                    % (AVOCADO, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc, (4, 0))

    def test_empty_file(self):
        cmd_line = ("%s run --job-results-dir %s -m optional_plugins/"
                    "varianter_yaml_to_mux/tests/.data/empty_file "
                    "-- examples/tests/passtest.py" % (AVOCADO, self.tmpdir.name))
        self.run_and_check(cmd_line, exit_codes.AVOCADO_ALL_OK, (1, 0))

    def test_run_mplex_params(self):
        for variant_msg in (('/run/short', 'A'),
                            ('/run/medium', 'ASDFASDF'),
                            ('/run/long', 'This is very long\nmultiline\ntext.')):
            variant, msg = variant_msg
            cmd_line = ('%s run --job-results-dir %s --disable-sysinfo '
                        '--test-runner=runner '
                        'examples/tests/env_variables.sh '
                        '-m examples/tests/env_variables.sh.data/env_variables.yaml '
                        '--mux-filter-only %s'
                        % (AVOCADO, self.tmpdir.name, variant))
            expected_rc = exit_codes.AVOCADO_ALL_OK
            result = self.run_and_check(cmd_line, expected_rc)

            log_files = glob.glob(os.path.join(self.tmpdir.name, 'latest',
                                               'test-results', '*', 'debug.log'))
            result = ''
            for log_file in log_files:
                result += genio.read_file(log_file)

            msg_lines = msg.splitlines()
            msg_header = '[stdout] Custom variable: %s' % msg_lines[0]
            self.assertIn(msg_header, result,
                          "Multiplexed variable should produce:"
                          "\n  %s\nwhich is not present in the output:\n  %s"
                          % (msg_header, "\n  ".join(result.splitlines())))
            for msg_remain in msg_lines[1:]:
                self.assertIn('[stdout] %s' % msg_remain, result,
                              "Multiplexed variable should produce:"
                              "\n  %s\nwhich is not present in the output:\n  %s"
                              % (msg_remain, "\n  ".join(result.splitlines())))

    def tearDown(self):
        self.tmpdir.cleanup()


class ReplayTests(unittest.TestCase):

    def setUp(self):
        prefix = 'avocado__%s__%s__%s__' % (__name__, 'ReplayTests', 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)
        cmd_line = ('%s run passtest.py '
                    '-m examples/tests/sleeptest.py.data/sleeptest.yaml '
                    '--job-results-dir %s --disable-sysinfo --json -'
                    % (AVOCADO, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)
        self.jobdir = ''.join(glob.glob(os.path.join(self.tmpdir.name, 'job-*')))
        idfile = ''.join(os.path.join(self.jobdir, 'id'))
        with open(idfile, 'r') as f:
            self.jobid = f.read().strip('\n')

    def run_and_check(self, cmd_line, expected_rc):
        os.chdir(BASEDIR)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        return result

    def tearDown(self):
        self.tmpdir.cleanup()


class DryRun(unittest.TestCase):

    def test_dry_run(self):
        cmd = ("%s run --disable-sysinfo --dry-run --dry-run-no-cleanup --json - "
               "--test-runner=runner "
               "--mux-inject foo:1 bar:2 baz:3 foo:foo:a "
               "foo:bar:b foo:baz:c bar:bar:bar "
               "-- examples/tests/passtest.py "
               "examples/tests/failtest.py "
               "examples/tests/gendata.py " % AVOCADO)
        number_of_tests = 3
        result = json.loads(process.run(cmd).stdout_text)
        log = ''
        for test in result['tests']:
            debuglog = test['logfile']
            log += genio.read_file(debuglog)
        # Remove the result dir
        shutil.rmtree(os.path.dirname(os.path.dirname(debuglog)))
        self.assertIn(tempfile.gettempdir(), debuglog)   # Use tmp dir, not default location
        self.assertEqual(result['job_id'], u'0' * 40)
        # Check if all tests were skipped
        self.assertEqual(result['cancel'], number_of_tests)
        for i in range(number_of_tests):
            test = result['tests'][i]
            self.assertEqual(test['fail_reason'],
                             u'Test cancelled due to --dry-run')
        # Check if all params are listed
        # The "/:bar ==> 2 is in the tree, but not in any leave so inaccessible
        # from test.
        for line in ("/:foo ==> 1", "/:baz ==> 3", "/foo:foo ==> a",
                     "/foo:bar ==> b", "/foo:baz ==> c", "/bar:bar ==> bar"):
            self.assertEqual(log.count(line), number_of_tests,
                             "Avocado log count for param '%s' not as expected:\n%s" % (line, log))


if __name__ == '__main__':
    unittest.main()
