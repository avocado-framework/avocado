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
        result = process.run(f"{AVOCADO} distro")
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertIn(b"Detected distribution", result.stdout)

    def test_app_error_stderr(self):
        """
        Checks that the application error (> level info) goes to stderr
        """
        result = process.run(f"{AVOCADO} unknown-whacky-command", ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
        self.assertIn(b"invalid choice: 'unknown-whacky-command'", result.stderr)
        self.assertNotIn(b"invalid choice: 'unknown-whacky-command'", result.stdout)
        self.assertIn(b"Avocado Test Runner", result.stdout)
        self.assertNotIn(b"Avocado Test Runner", result.stderr)

    def test_other_stream_early_stdout(self):
        """
        Checks that other streams (early in this case) goes to stdout

        Also checks the symmetry between `--show early` and the environment
        variable `AVOCADO_LOG_EARLY` being set.
        """
        cmds = (
            (
                f"{AVOCADO} --show early run --disable-sysinfo "
                f"--job-results-dir {self.tmpdir.name} "
                f"examples/tests/passtest.py",
                {},
            ),
            (
                f"{AVOCADO} run --disable-sysinfo "
                f"--job-results-dir {self.tmpdir.name} "
                f"examples/tests/passtest.py",
                {"AVOCADO_LOG_EARLY": "y"},
            ),
        )
        for cmd, env in cmds:
            result = process.run(cmd, env=env, shell=True)
            # Avocado will see the main module on the command line
            cmd_in_log = os.path.join(BASEDIR, "avocado", "__main__.py")
            self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
            self.assertIn(
                f"avocado.job: Command line: {cmd_in_log}", result.stdout_text
            )

    def test_test(self):
        """
        Checks that the test stream (early in this case) goes to stdout
        """
        cmd = (
            f"{AVOCADO} --show=job run --disable-sysinfo "
            f"--job-results-dir {self.tmpdir.name} "
            f"examples/tests/passtest.py"
        )
        result = process.run(cmd)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        # Avocado will see the main module on the command line
        cmd_in_log = os.path.join(BASEDIR, "avocado", "__main__.py")
        self.assertIn(f"Command line: {cmd_in_log}", result.stdout_text)
        self.assertIn(
            b"\navocado.job: examples/tests/passtest.py:PassTest.test: STARTED\n",
            result.stdout,
        )
        self.assertIn(
            b"\navocado.job: examples/tests/passtest.py:PassTest.test: PASS\n",
            result.stdout,
        )

    def test_none_success(self):
        """
        Checks that only errors are output, and that they go to stderr
        """
        cmd = (
            f"{AVOCADO} --show none run --disable-sysinfo "
            f"--job-results-dir {self.tmpdir.name} "
            f"examples/tests/passtest.py"
        )
        result = process.run(cmd)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEqual(b"", result.stdout)

    def test_none_error(self):
        """
        Checks that only errors are output, and that they go to stderr
        """
        cmd = f"{AVOCADO} --show=none unknown-whacky-command"
        result = process.run(cmd, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
        self.assertEqual(b"", result.stdout)
        self.assertNotEqual(b"", result.stderr)

    def test_custom_stream_and_level(self):
        """
        Checks if "--show stream:level" works for non-built-in-streams
        """

        def run(show, no_lines):
            result = process.run(f"{AVOCADO} --show {show} config")
            out = result.stdout.splitlines()
            if no_lines == "more_than_one":
                self.assertGreater(
                    len(out),
                    1,
                    (
                        f"Output of {result.command} should "
                        f"contain more than 1 line, contains only "
                        f"{len(out)}\n{result}"
                    ),
                )
            else:
                self.assertEqual(
                    len(out),
                    no_lines,
                    (
                        f"Output of {result.command} should "
                        f"contain {no_lines} lines, contains "
                        f"{len(out)} instead\n{result}"
                    ),
                )

        run("avocado.app:dEbUg", "more_than_one")
        run("avocado.app:0", "more_than_one")
        run("avocado.app:InFo", 1)
        run("avocado.app:20", 1)
        run("avocado.app:wARn", 0)
        run("avocado.app:30", 0)

    def test_job_log_separation(self):
        """
        Checks that job.log doesn't have logs from other streams.
        """
        cmd = (
            f"{AVOCADO} --show none run --disable-sysinfo "
            f"--job-results-dir {self.tmpdir.name} "
            f"examples/tests/passtest.py"
        )
        result = process.run(cmd)
        job_log_path = os.path.join(self.tmpdir.name, "latest", "job.log")
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        with open(job_log_path, "rb") as job_log_file:
            wrong_lines = list(
                filter(
                    lambda x: b"job" not in x and b"testlogs" not in x,
                    job_log_file.readlines(),
                )
            )
            self.assertEqual(
                len(wrong_lines),
                0,
                "job.log has different logging streams than avocado.job",
            )

    def test_logs_duplication(self):
        """
        Checks that job.log doesn't have duplicated lines.
        """
        cmd = (
            f"{AVOCADO} --show none run --disable-sysinfo "
            f"--job-results-dir {self.tmpdir.name} "
            f"examples/tests/passtest.py"
        )
        result = process.run(cmd)
        job_log_path = os.path.join(self.tmpdir.name, "latest", "job.log")
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        with open(job_log_path, "rt", encoding="utf-8") as job_log:
            lines = [line.split("|", 1)[1] for line in job_log.readlines()]
            lines = list(filter(lambda x: (x.replace(" ", "") != "\n"), lines))
            self.assertEqual(
                len(lines), len(set(lines)), "job_log has duplicated lines."
            )

    def test_default_streams(self):
        """
        Checks that avocado default streams are properly handled.
        """
        cmd = (
            f"{AVOCADO} run --disable-sysinfo "
            f"--job-results-dir {self.tmpdir.name} "
            f"examples/tests/logging_streams.py"
        )
        result = process.run(cmd)
        job_dir = os.path.join(self.tmpdir.name, "latest")
        job_log_path = os.path.join(job_dir, "job.log")
        test_log_path = os.path.join(
            job_dir,
            "test-results",
            "1-examples_tests_logging_streams.py_Plant.test_plant_organic",
            "debug.log",
        )
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        with open(job_log_path, "rb") as log:
            self.assertNotIn(b"Seeds have been palanted.", log.read())
        with open(test_log_path, "rb") as log:
            result = log.read()
            self.assertIn(b"waiting for Avocados to grow", result)
            self.assertIn(b"Seeds have been palanted.", result)


if __name__ == "__main__":
    unittest.main()
