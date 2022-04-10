import json
import os

from avocado.utils import process
from selftests.utils import AVOCADO, TestCaseTmpDir


class ByStatusTest(TestCaseTmpDir):

    def test_symlinks(self):
        result = process.run(f"{AVOCADO} run "
                             f"--job-results-dir {self.tmpdir.name} "
                             f"--disable-sysinfo --json - "
                             f"/bin/true /bin/false", ignore_status=True)
        res = json.loads(result.stdout_text)

        for test in res['tests']:
            logdir = test['logdir']
            status = test['status']
            where = os.path.dirname(logdir)
            basename = os.path.basename(logdir)
            link = os.path.join(where, 'by-status', status, basename)
            self.assertTrue(os.path.exists(os.readlink(link)))
