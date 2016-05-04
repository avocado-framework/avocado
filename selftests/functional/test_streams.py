import os
import shutil
import sys
import tempfile

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import exit_codes
from avocado.utils import process


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


class StreamsTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def test_app_info_stdout(self):
        """
        Checks that the application output (<= level info) goes to stdout
        """
        result = process.run('./scripts/avocado distro')
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertIn('Detected distribution', result.stdout)
        self.assertEqual('', result.stderr)

    def test_app_error_stderr(self):
        """
        Checks that the application error (> level info) goes to stderr
        """
        result = process.run('./scripts/avocado unknown-whacky-command',
                             ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
        self.assertIn("invalid choice: 'unknown-whacky-command'",
                      result.stderr)
        self.assertNotIn("invalid choice: 'unknown-whacky-command'",
                         result.stdout)
        self.assertIn("Avocado Test Runner", result.stdout)
        self.assertNotIn("Avocado Test Runner", result.stderr)

    def test_other_stream_early_stdout(self):
        """
        Checks that other streams (early in this case) goes to stdout

        Also checks the symmetry between `--show early` and the environment
        variable `AVOCADO_LOG_EARLY` being set.
        """
        cmds = (('./scripts/avocado --show early run --sysinfo=off '
                 '--job-results-dir %s passtest.py' % self.tmpdir, {}),
                ('./scripts/avocado run --sysinfo=off --job-results-dir'
                 ' %s passtest.py' % self.tmpdir, {'AVOCADO_LOG_EARLY': 'y'}))
        for cmd, env in cmds:
            result = process.run(cmd, env=env, shell=True)
            self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
            self.assertIn("stevedore.extension: found extension EntryPoint.parse",
                          result.stdout)
            self.assertIn("avocado.test: Command line: %s" % cmd,
                          result.stdout)
            self.assertEqual('', result.stderr)

    def test_test(self):
        """
        Checks that the test stream (early in this case) goes to stdout

        Also checks the symmetry between `--show test` and `--show-job-log`
        """
        for cmd in (('./scripts/avocado --show test run --sysinfo=off '
                     '--job-results-dir %s passtest.py' % self.tmpdir),
                    ('./scripts/avocado run --show-job-log --sysinfo=off '
                     '--job-results-dir %s passtest.py' % self.tmpdir)):
            result = process.run(cmd)
            self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
            self.assertNotIn("stevedore.extension: found extension EntryPoint.parse",
                             result.stdout)
            self.assertNotIn("stevedore.extension: found extension EntryPoint.parse",
                             result.stderr)
            self.assertIn("Command line: %s" % cmd,
                          result.stdout)
            self.assertIn("\nSTART 1-passtest.py:PassTest.test",
                          result.stdout)
            self.assertIn("PASS 1-passtest.py:PassTest.test", result.stdout)
            self.assertEqual('', result.stderr)

    def test_none_success(self):
        """
        Checks that only errors are output, and that they go to stderr

        Also checks the symmetry between `--show none` and `--silent`
        """
        for cmd in (('./scripts/avocado --show none run --sysinfo=off '
                     '--job-results-dir %s passtest.py' % self.tmpdir),
                    ('./scripts/avocado --silent run --sysinfo=off '
                     '--job-results-dir %s passtest.py' % self.tmpdir)):
            result = process.run(cmd)
            self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
            self.assertEqual('', result.stdout)
            self.assertEqual('', result.stderr)

    def test_none_error(self):
        """
        Checks that only errors are output, and that they go to stderr

        Also checks the symmetry between `--show none` and `--silent`
        """
        for cmd in ('./scripts/avocado --show none unknown-whacky-command',
                    './scripts/avocado --silent unknown-whacky-command'):
            result = process.run(cmd, ignore_status=True)
            self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
            self.assertEqual('', result.stdout)
            self.assertNotEqual('', result.stderr)

    def test_custom_stream_and_level(self):
        """
        Checks if "--show stream:level" works for non-built-in-streams
        """
        def run(show, no_lines):
            result = process.run("./scripts/avocado --show %s config" % show)
            out = (result.stdout + result.stderr).splitlines()
            if no_lines == "more_than_one":
                self.assertGreater(len(out), 1, "Output of %s should contain "
                                   "more than 1 line, contains only %s\n%s"
                                   % (result.command, len(out), result))
            else:
                self.assertEqual(len(out), no_lines, "Output of %s should "
                                 "contain %s lines, contains %s instead\n%s"
                                 % (result.command, no_lines, len(out),
                                    result))
        run("avocado.app:dEbUg", "more_than_one")
        run("avocado.app:0", "more_than_one")
        run("avocado.app:InFo", 1)
        run("avocado.app:20", 1)
        run("avocado.app:wARn", 0)
        run("avocado.app:30", 0)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
