import tempfile

from avocado.core.job import Job
from avocado.utils import script
from avocado.utils.network.ports import find_free_port
from selftests.utils import (TestCaseTmpDir, skipUnlessPathExists,
                             temp_dir_prefix)

SCRIPT_CONTENT = """#!/bin/bash
/bin/sleep 30
"""


class TaskTimeOutTest(TestCaseTmpDir):

    def setUp(self):
        super(TaskTimeOutTest, self).setUp()
        self.script = script.TemporaryScript(
            'sleep.sh',
            SCRIPT_CONTENT,
            'avocado_timeout_functional')
        self.script.save()

        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    @skipUnlessPathExists('/bin/sleep')
    def test_sleep_longer_timeout(self):
        status_server = '127.0.0.1:%u' % find_free_port()
        config = {'run.references': [self.script.path],
                  'nrunner.status_server_listen': status_server,
                  'nrunner.status_server_uri': status_server,
                  'run.results_dir': self.tmpdir.name,
                  'run.keep_tmp': True,
                  'task.timeout.running': 2,
                  'run.test_runner': 'nrunner'}

        with Job.from_config(job_config=config) as job:
            job.run()

        self.assertEqual(1, job.result.skipped)
        self.assertEqual(0, job.result.passed)

    def tearDown(self):
        super(TaskTimeOutTest, self).tearDown()
        self.script.remove()
