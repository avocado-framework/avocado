import os

from avocado import Test
from avocado.core import exit_codes
from avocado.core.job import Job
from avocado.utils import script
from selftests.utils import TestCaseTmpDir


class ExecTestRunnerTest(TestCaseTmpDir, Test):
    def test_env_variables(self):
        commands_path = os.path.join(self.tmpdir.name, "commands")
        script.make_script(commands_path, "uname -a")
        base_config = {
            "run.results_dir": self.tmpdir.name,
            "sysinfo.collect.per_test": True,
            "sysinfo.collectibles.commands": commands_path,
            "resolver.references": ["examples/tests/env_variables.sh"],
        }
        with Job.from_config(base_config) as j:
            result = j.run()
        logfile_path = os.path.join(
            self.tmpdir.name,
            "latest",
            "test-results",
            "1-1-examples_tests_env_variables.sh",
            "debug.log",
        )
        with open(logfile_path, "rb") as f:
            for line in f.readlines():
                self.log.debug(line)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(
            result,
            expected_rc,
            (f"Avocado did not return rc " f"{int(expected_rc)}:\n{result}"),
        )
