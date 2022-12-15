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
        self.tmpdir = tempfile.TemporaryDirectory(prefix="avocado_" + __name__)

    def run_and_check(self, cmd_line, expected_rc, tests=None):
        os.chdir(BASEDIR)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(
            result.exit_status,
            expected_rc,
            (f"Command {cmd_line} did not return rc " f"{expected_rc}:\n{result}"),
        )
        if tests is not None:
            exp = (
                "PASS %s | ERROR 0 | FAIL %s | SKIP 0 | WARN 0 | "  # pylint: disable=C0209
                "INTERRUPT 0" % tests
            )
            self.assertIn(exp, result.stdout_text, f"{exp} not in stdout:\n{result}")
        return result

    def test_mplex_plugin(self):
        cmd_line = (
            f"{AVOCADO} variants -m examples/tests/sleeptest.py.data/" f"sleeptest.yaml"
        )
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)

    def test_mplex_plugin_nonexistent(self):
        cmd_line = f"{AVOCADO} variants -m nonexist"
        expected_rc = exit_codes.AVOCADO_FAIL
        result = self.run_and_check(cmd_line, expected_rc)
        self.assertIn("No such file or directory", result.stderr_text)

    def test_mplex_plugin_using(self):
        cmd_line = (
            f"{AVOCADO} variants "
            f"-m /:optional_plugins/varianter_yaml_to_mux/"
            f"tests/.data/mux-selftest-using.yaml"
        )
        expected_rc = exit_codes.AVOCADO_ALL_OK
        result = self.run_and_check(cmd_line, expected_rc)
        self.assertIn(b" /foo/baz/bar", result.stdout)

    def test_run_mplex_noid(self):
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo "
            f"-m examples/tests/sleeptest.py.data/sleeptest.yaml"
        )
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        self.run_and_check(cmd_line, expected_rc)

    def test_run_mplex_passtest(self):
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo "
            f"examples/tests/passtest.py -m "
            f"examples/tests/sleeptest.py.data/sleeptest.yaml"
        )
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc, (4, 0))
        # Also check whether jobdata contains correct parameter paths
        with open(
            os.path.join(self.tmpdir.name, "latest", "jobdata", "variants-1.json"),
            encoding="utf-8",
        ) as variants_file:
            variants = variants_file.read()
        self.assertIn(
            '["/run/*"]',
            variants,
            (
                f"parameter paths stored in jobdata does not contains "
                f'["/run/*"]\n{variants}"'
            ),
        )

    def test_run_mplex_doublepass(self):
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo "
            f"examples/tests/passtest.py "
            f"examples/tests/passtest.py -m "
            f"examples/tests/sleeptest.py.data/sleeptest.yaml "
            f"--mux-path /foo/\\* /bar/\\* /baz/\\*"
        )
        self.run_and_check(cmd_line, exit_codes.AVOCADO_ALL_OK, (8, 0))
        # Also check whether jobdata contains correct parameter paths
        with open(
            os.path.join(self.tmpdir.name, "latest", "jobdata", "variants-1.json"),
            encoding="utf-8",
        ) as variants_file:
            variants = variants_file.read()
        exp = '["/foo/*", "/bar/*", "/baz/*"]'
        self.assertIn(
            exp,
            variants,
            (
                f"parameter paths stored in jobdata does not contains "
                f"{exp}\n{variants}"
            ),
        )

    def test_run_mplex_failtest(self):
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo "
            f"examples/tests/passtest.py "
            f"examples/tests/failtest.py -m "
            f"examples/tests/sleeptest.py.data/sleeptest.yaml"
        )
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        result = self.run_and_check(cmd_line, expected_rc, (4, 4))
        self.assertIn(
            b"(1/8) examples/tests/passtest.py:PassTest.test;run-short-beaf",
            result.stdout,
        )
        self.assertIn(
            b"(2/8) examples/tests/passtest.py:PassTest.test;run-medium-5595",
            result.stdout,
        )
        self.assertIn(
            b"(8/8) examples/tests/failtest.py:FailTest.test;run-longest-efc4",
            result.stdout,
        )

    def test_run_mplex_failtest_tests_per_variant(self):
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo "
            f"examples/tests/passtest.py "
            f"examples/tests/failtest.py -m "
            f"examples/tests/sleeptest.py.data/sleeptest.yaml "
            f"--execution-order tests-per-variant"
        )
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        result = self.run_and_check(cmd_line, expected_rc, (4, 4))
        self.assertIn(
            b"(1/8) examples/tests/passtest.py:PassTest.test;run-short-beaf",
            result.stdout,
        )
        self.assertIn(
            b"(2/8) examples/tests/failtest.py:FailTest.test;run-short-beaf",
            result.stdout,
        )
        self.assertIn(
            b"(8/8) examples/tests/failtest.py:FailTest.test;run-longest-efc4",
            result.stdout,
        )

    def test_run_double_mplex(self):
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo "
            f"examples/tests/passtest.py -m "
            f"examples/tests/sleeptest.py.data/sleeptest.yaml "
            f"examples/tests/sleeptest.py.data/sleeptest.yaml"
        )
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc, (4, 0))

    def test_empty_file(self):
        cmd_line = (
            f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
            f" -m optional_plugins/"
            f"varianter_yaml_to_mux/tests/.data/empty_file "
            f"-- examples/tests/passtest.py"
        )
        self.run_and_check(cmd_line, exit_codes.AVOCADO_ALL_OK, (1, 0))

    def test_run_mplex_params(self):
        for variant_msg in (
            ("/run/short", "A"),
            ("/run/medium", "ASDFASDF"),
            ("/run/long", "This is very long\nmultiline\ntext."),
        ):
            variant, msg = variant_msg
            cmd_line = (
                f"{AVOCADO} run --job-results-dir {self.tmpdir.name} "
                f"--disable-sysinfo "
                f"examples/tests/custom_env_variable.sh "
                f"-m examples/tests/custom_env_variable.sh.data/"
                f"variants.yaml --mux-filter-only {variant}"
            )
            expected_rc = exit_codes.AVOCADO_ALL_OK
            result = self.run_and_check(cmd_line, expected_rc)

            log_files = glob.glob(
                os.path.join(
                    self.tmpdir.name, "latest", "test-results", "*", "debug.log"
                )
            )
            result = ""
            for log_file in log_files:
                result += genio.read_file(log_file)

            msg_lines = msg.splitlines()
            msg_header = f"[stdout] Custom variable: {msg_lines[0]}"
            self.assertIn(
                msg_header,
                result,
                "Multiplexed variable should produce:"
                "\n  %s\nwhich is not present in the output:\n  %s"
                % (msg_header, "\n  ".join(result.splitlines())),
            )
            for msg_remain in msg_lines[1:]:
                self.assertIn(
                    f"[stdout] {msg_remain}",
                    result,
                    "Multiplexed variable should produce:"
                    "\n  %s\nwhich is not present in the output:\n  %s"
                    % (msg_remain, "\n  ".join(result.splitlines())),
                )

    def test_mux_inject(self):
        cmd = (
            f"{AVOCADO} run --disable-sysinfo --json - "
            f"--job-results-dir {self.tmpdir.name} "
            f"--mux-inject foo:1 bar:2 baz:3 foo:foo:a "
            f"foo:bar:b foo:baz:c bar:bar:bar "
            f"-- examples/tests/params.py "
            f"examples/tests/params.py "
            f"examples/tests/params.py "
        )
        number_of_tests = 3
        result = json.loads(process.run(cmd).stdout_text)
        log = ""
        for test in result["tests"]:
            debuglog = test["logfile"]
            log += genio.read_file(debuglog)
        # Remove the result dir
        shutil.rmtree(os.path.dirname(os.path.dirname(debuglog)))
        self.assertIn(tempfile.gettempdir(), log)  # Use tmp dir, not default location
        # Check if all params are listed
        # The "/:bar ==> 2 is in the tree, but not in any leave so inaccessible
        # from test.
        for line in (
            "/:foo ==> 1",
            "/:baz ==> 3",
            "/foo:foo ==> a",
            "/foo:bar ==> b",
            "/foo:baz ==> c",
            "/bar:bar ==> bar",
        ):
            self.assertEqual(
                log.count(line),
                number_of_tests,
                (f"Avocado log count for param '{line}' " f"not as expected:\n{log}"),
            )

    def tearDown(self):
        self.tmpdir.cleanup()


class ReplayTests(unittest.TestCase):
    def setUp(self):
        prefix = f"avocado__{__name__}__{'ReplayTests'}__{'setUp'}__"
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)
        cmd_line = (
            f"{AVOCADO} run passtest.py "
            f"-m examples/tests/sleeptest.py.data/sleeptest.yaml "
            f"--job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo --json -"
        )
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)
        self.jobdir = "".join(glob.glob(os.path.join(self.tmpdir.name, "job-*")))
        idfile = "".join(os.path.join(self.jobdir, "id"))
        with open(idfile, "r", encoding="utf-8") as f:
            self.jobid = f.read().strip("\n")

    def run_and_check(self, cmd_line, expected_rc):
        os.chdir(BASEDIR)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(
            result.exit_status,
            expected_rc,
            (f"Command {cmd_line} did not return rc " f"{expected_rc}:\n{result}"),
        )
        return result

    def tearDown(self):
        self.tmpdir.cleanup()


if __name__ == "__main__":
    unittest.main()
