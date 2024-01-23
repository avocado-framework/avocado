import os

from avocado import Test
from avocado.utils import process
from selftests.utils import AVOCADO

WRONG_CONFIG = """
[job.output.testlogs]
statuses = ["CANCEL", "SKIP", "FAIL"]
	foo moo
"""


class SettingsTest(Test):
    def test_wrong_config(self):
        config_path = os.path.join(self.workdir, "config")
        with open(config_path, mode="w", encoding="utf-8") as config_file:
            config_file.write(WRONG_CONFIG)
        result = process.run(
            f"{AVOCADO} --config={config_path} run "
            f"--job-results-dir {self.workdir} "
            f"--disable-sysinfo -- examples/tests/passtest.py",
            ignore_status=True,
        )
        self.assertIn(
            f'Avocado crashed unexpectedly: Syntax error in config file {config_path}, please check the value ["CANCEL", "SKIP", "FAIL"]\nfoo moo \n',
            result.stderr_text,
        )
