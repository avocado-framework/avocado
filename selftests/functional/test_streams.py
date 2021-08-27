import os
import unittest

from avocado.core import exit_codes
from avocado.utils import process
from selftests.utils import AVOCADO, BASEDIR, TestCaseTmpDir


class StreamsTest(TestCaseTmpDir):

    def test_app_info_stdout(self):
        """
        Checks that the application output (<= level info) goes to stdout
        """
        result = process.run('%s distro' % AVOCADO)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertIn(b'Detected distribution', result.stdout)

    def test_app_error_stderr(self):
        """
        Checks that the application error (> level info) goes to stderr
        """
        result = process.run('%s unknown-whacky-command' % AVOCADO,
                             ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
        self.assertIn(b"invalid choice: 'unknown-whacky-command'",
                      result.stderr)
        self.assertNotIn(b"invalid choice: 'unknown-whacky-command'",
                         result.stdout)
        self.assertIn(b"Avocado Test Runner", result.stdout)
        self.assertNotIn(b"Avocado Test Runner", result.stderr)

    def test_other_stream_early_stdout(self):
        """
        Checks that other streams (early in this case) goes to stdout

        Also checks the symmetry between `--show early` and the environment
        variable `AVOCADO_LOG_EARLY` being set.
        """
        cmds = (('%s --show early run --disable-sysinfo '
                 '--job-results-dir %s examples/tests/passtest.py'
                 % (AVOCADO, self.tmpdir.name),
                 {}),
                ('%s run --disable-sysinfo --job-results-dir'
                 ' %s examples/tests/passtest.py'
                 % (AVOCADO, self.tmpdir.name),
                 {'AVOCADO_LOG_EARLY': 'y'}))
        for cmd, env in cmds:
            result = process.run(cmd, env=env, shell=True)
            # Avocado will see the main module on the command line
            cmd_in_log = os.path.join(BASEDIR, 'avocado', '__main__.py')
            self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
            self.assertIn("avocado.test: Command line: %s" % cmd_in_log,
                          result.stdout_text)

    def test_test(self):
        """
        Checks that the test stream (early in this case) goes to stdout
        """
        cmd = ('%s --show=test run --disable-sysinfo --job-results-dir %s '
               '--test-runner=runner '
               'examples/tests/passtest.py' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        # Avocado will see the main module on the command line
        cmd_in_log = os.path.join(BASEDIR, 'avocado', '__main__.py')
        self.assertIn("Command line: %s" % cmd_in_log,
                      result.stdout_text)
        self.assertIn(b"\nSTART 1-examples/tests/passtest.py:PassTest.test",
                      result.stdout)
        self.assertIn(b"PASS 1-examples/tests/passtest.py:PassTest.test",
                      result.stdout)

    def test_none_success(self):
        """
        Checks that only errors are output, and that they go to stderr
        """
        cmd = ('%s --show none run --disable-sysinfo --job-results-dir %s '
               'examples/tests/passtest.py' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEqual(b'', result.stdout)

    def test_none_error(self):
        """
        Checks that only errors are output, and that they go to stderr
        """
        cmd = '%s --show=none unknown-whacky-command' % AVOCADO
        result = process.run(cmd, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
        self.assertEqual(b'', result.stdout)
        self.assertNotEqual(b'', result.stderr)

    def test_custom_stream_and_level(self):
        """
        Checks if "--show stream:level" works for non-built-in-streams
        """
        def run(show, no_lines):
            result = process.run("%s --show %s config" % (AVOCADO, show))
            out = result.stdout.splitlines()
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


if __name__ == '__main__':
    unittest.main()
