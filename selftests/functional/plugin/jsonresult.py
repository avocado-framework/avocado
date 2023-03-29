import json
from os import path

from avocado.utils import process
from selftests.utils import AVOCADO, TestCaseTmpDir


class JsonResultTest(TestCaseTmpDir):
    def test_logfile(self):
        cmd_line = (
            f"{AVOCADO} run examples/tests/failtest.py "
            f"--job-results-dir {self.tmpdir.name} --disable-sysinfo"
        )
        process.run(cmd_line, ignore_status=True)
        json_path = path.join(self.tmpdir.name, "latest", "results.json")

        with open(json_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
            test_data = data["tests"].pop()
            expected_logfile = path.join(test_data["logdir"], "debug.log")
            self.assertEqual(expected_logfile, test_data["logfile"])

    def test_fail_reason(self):
        cmd_line = (
            f"{AVOCADO} run examples/tests/failtest.py "
            f"--job-results-dir {self.tmpdir.name} --disable-sysinfo"
        )
        process.run(cmd_line, ignore_status=True)
        json_path = path.join(self.tmpdir.name, "latest", "results.json")
        with open(json_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
            test_data = data["tests"].pop()
            self.assertEqual("This test is supposed to fail", test_data["fail_reason"])

    def test_tags_in_result(self):
        cmd_line = (
            f"{AVOCADO} run examples/tests/failtest.py "
            f"--job-results-dir {self.tmpdir.name} --disable-sysinfo"
        )
        process.run(cmd_line, ignore_status=True)
        json_path = path.join(self.tmpdir.name, "latest", "results.json")
        with open(json_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
            test_data = data["tests"][0]
            self.assertEqual({"failure_expected": None}, test_data["tags"])

    def test_variant(self):
        cmd_line = (
            f"{AVOCADO} run examples/tests/passtest.py "
            "--mux-yaml examples/yaml_to_mux/simple_vars.yaml "
            f"--job-results-dir {self.tmpdir.name} --disable-sysinfo "
            "--max-parallel-tasks=1"
        )
        process.run(cmd_line, ignore_status=True)
        json_path = path.join(self.tmpdir.name, "latest", "results.json")
        with open(json_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
            test_data = data["tests"][0]
            self.assertEqual(
                "examples/tests/passtest.py:PassTest.test;run-first-febe",
                test_data["name"],
            )
            test_data = data["tests"][1]
            self.assertEqual(
                "examples/tests/passtest.py:PassTest.test;run-second-bafe",
                test_data["name"],
            )
