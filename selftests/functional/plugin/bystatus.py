import json
import os

from avocado.utils import process
from selftests.utils import AVOCADO, TestCaseTmpDir


class ByStatusTest(TestCaseTmpDir):
    def test_symlinks(self):
        result = process.run(
            f"{AVOCADO} run "
            f"--job-results-dir {self.tmpdir.name} "
            f"--disable-sysinfo --json - "
            f"examples/tests/true examples/tests/false",
            ignore_status=True,
        )
        res = json.loads(result.stdout_text)

        for test in res["tests"]:
            logdir = test["logdir"]
            status = test["status"]
            where = os.path.dirname(logdir)
            basename = os.path.basename(logdir)
            status_dir = os.path.join(where, "by-status", status)
            link = os.path.join(status_dir, basename)
            sym_link = os.readlink(link)
            self.assertTrue(os.path.exists(os.path.join(status_dir, sym_link)))
            self.assertTrue(os.path.samefile(logdir, link))
