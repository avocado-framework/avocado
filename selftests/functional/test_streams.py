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
        result = process.run(f'{AVOCADO} distro')
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertIn(b'Detected distribution', result.stdout)

    def test_app_error_stderr(self):
        """
        Checks that the application error (> level info) goes to stderr
        """
        result = process.run(f'{AVOCADO} unknown-whacky-command',
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
        cmds = ((f'{AVOCADO} --show early run --disable-sysinfo '
                 f'--job-results-dir {self.tmpdir.name} '
                 f'examples/tests/passtest.py', {}),
                (f'{AVOCADO} run --disable-sysinfo '
                 f'--job-results-dir {self.tmpdir.name} '
                 f'examples/tests/passtest.py',
                 {'AVOCADO_LOG_EARLY': 'y'})
                )
        for cmd, env in cmds:
            result = process.run(cmd, env=env, shell=True)
            # Avocado will see the main module on the command line
            cmd_in_log = os.path.join(BASEDIR, 'avocado', '__main__.py')
            self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
            self.assertIn(f"avocado.test: Command line: {cmd_in_log}",
                          result.stdout_text)

    def test_test(self):
        """
        Checks that the test stream (early in this case) goes to stdout
        """
        cmd = (f'{AVOCADO} --show=test run --disable-sysinfo '
               f'--job-results-dir {self.tmpdir.name} '
               f'examples/tests/passtest.py')
        result = process.run(cmd)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        # Avocado will see the main module on the command line
        cmd_in_log = os.path.join(BASEDIR, 'avocado', '__main__.py')
        self.assertIn(f"Command line: {cmd_in_log}",
                      result.stdout_text)
        self.assertIn(b"\nexamples/tests/passtest.py:PassTest.test: STARTED\n",
                      result.stdout)
        self.assertIn(b"\nexamples/tests/passtest.py:PassTest.test: PASS\n",
                      result.stdout)

    def test_none_success(self):
        """
        Checks that only errors are output, and that they go to stderr
        """
        cmd = (f'{AVOCADO} --show none run --disable-sysinfo '
               f'--job-results-dir {self.tmpdir.name} '
               f'examples/tests/passtest.py')
        result = process.run(cmd)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEqual(b'', result.stdout)

    def test_none_error(self):
        """
        Checks that only errors are output, and that they go to stderr
        """
        cmd = f'{AVOCADO} --show=none unknown-whacky-command'
        result = process.run(cmd, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
        self.assertEqual(b'', result.stdout)
        self.assertNotEqual(b'', result.stderr)

    def test_custom_stream_and_level(self):
        """
        Checks if "--show stream:level" works for non-built-in-streams
        """
        def run(show, no_lines):
            result = process.run(f"{AVOCADO} --show {show} config")
            out = result.stdout.splitlines()
            if no_lines == "more_than_one":
                self.assertGreater(len(out), 1,
                                   (f"Output of {result.command} should "
                                    f"contain more than 1 line, contains only "
                                    f"{len(out)}\n{result}"))
            else:
                self.assertEqual(len(out), no_lines,
                                 (f"Output of {result.command} should "
                                  f"contain {no_lines} lines, contains "
                                  f"{len(out)} instead\n{result}"))
        run("avocado.app:dEbUg", "more_than_one")
        run("avocado.app:0", "more_than_one")
        run("avocado.app:InFo", 1)
        run("avocado.app:20", 1)
        run("avocado.app:wARn", 0)
        run("avocado.app:30", 0)


if __name__ == '__main__':
    unittest.main()
