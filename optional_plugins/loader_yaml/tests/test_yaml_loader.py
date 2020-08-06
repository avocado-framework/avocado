import os
import tempfile
import unittest

from avocado.core import exit_codes
from avocado.utils import process
from selftests import AVOCADO, BASEDIR, skipUnlessPathExists


class YamlLoaderTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix='avocado_' + __name__)

    def run_and_check(self, cmd_line, expected_rc, stdout_strings=None, stdout_excluded_strings=None):
        os.chdir(BASEDIR)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        if stdout_strings is not None:
            for exp in stdout_strings:
                self.assertIn(exp, result.stdout, "%s not in stdout:"
                              "\n%s" % (exp, result))
        if stdout_excluded_strings is not None:
            for exp in stdout_excluded_strings:
                self.assertNotIn(exp, result.stdout)
        return result

    def test_replay(self):
        # Run source job
        tests = [b"PASSTEST.PY PREFIX: passtest.py:PassTest.test",
                 b"passtest.sh", b"executes bin true"]
        not_tests = [b"failtest.py"]
        cmd = ('%s run --disable-sysinfo --job-results-dir %s -- '
               'optional_plugins/loader_yaml/tests/.data/two_tests.yaml'
               % (AVOCADO, self.tmpdir.name))
        res = self.run_and_check(cmd, exit_codes.AVOCADO_ALL_OK, tests,
                                 not_tests)
        # Run replay job
        for line in res.stdout.splitlines():
            if line.startswith(b"JOB LOG"):
                joblog = line[13:]
                srcjob = os.path.dirname(joblog)
                break
        else:
            self.fail("Unable to find 'JOB LOG' in:\n%s" % res)
        cmd = ('%s run --disable-sysinfo --job-results-dir %s '
               '--replay %s' % (AVOCADO, self.tmpdir.name, srcjob.decode('utf-8')))
        self.run_and_check(cmd, exit_codes.AVOCADO_ALL_OK, tests, not_tests)

    @skipUnlessPathExists('/bin/true')
    @skipUnlessPathExists('/bin/echo')
    def test_yaml_loader_list(self):
        # Verifies that yaml_loader list won't crash and is able to detect
        # various test types
        result = process.run("%s -V list --loaders yaml_testsuite -- "
                             "examples/yaml_to_mux_loader/loaders.yaml"
                             % AVOCADO)
        # This has to be defined like this as pep8 complains about tailing
        # empty spaces when using """
        self.assertRegex(result.stdout_text, r"Type *Test *Tag\(s\)\n"
                                             r"INSTRUMENTED *passtest.py:PassTest.test * fast\n"
                                             r"SIMPLE.*passtest.sh *\n"
                                             r"EXTERNAL *external_echo *\n"
                                             r"EXTERNAL *external_false *\n")
        # Also check whether list without loaders won't crash
        result = process.run("%s -V list -- "
                             "examples/yaml_to_mux_loader/loaders.yaml"
                             % AVOCADO)

    def test_yaml_loader_run(self):
        # Checks that yaml_loader supplies correct params and that
        # --mux-suite-only filters the test suite
        result = process.run("%s --show test run --dry-run --mux-suite-only "
                             "/run/tests/sleeptest -- examples/yaml_to_mux_"
                             "loader/advanced.yaml" % AVOCADO)
        test = -1
        exp_timeouts = [2] * 4 + [6] * 4 + [None] * 4
        exp_timeout = None
        exp_sleep_lengths = [0.5, 1, 5, 10] * 3
        exp_sleep_length = None
        for line in result.stdout_text.splitlines():
            if line.startswith("START "):
                self.assertFalse(exp_timeout, "%s was not found in test %ss "
                                 "output:\n%s" % (exp_timeout, test, result))
                self.assertFalse(exp_timeout, "%s was not found in test %ss "
                                 "output:\n%s" % (exp_sleep_length, test,
                                                  result))
                self.assertLess(test, 12, "Number of tests is greater than "
                                "12:\n%s" % result)
                test += 1
                timeout = exp_timeouts[test]
                if timeout:
                    exp_timeout = "timeout ==> %s" % timeout
                else:
                    exp_timeout = "(key=timeout, path=*, default=None) => None"
                exp_sleep_length = ("sleep_length ==> %s"
                                    % exp_sleep_lengths[test])
            elif exp_timeout and exp_timeout in line:
                exp_timeout = None
            elif exp_sleep_length and exp_sleep_length in line:
                exp_sleep_length = None
        self.assertEqual(test, 11, "Number of tests is not 12 (%s):\n%s"
                         % (test, result))

    def tearDown(self):
        self.tmpdir.cleanup()


if __name__ == '__main__':
    unittest.main()
