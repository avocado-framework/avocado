from avocado.core.job import Job
from avocado.utils import script
from selftests.utils import TestCaseTmpDir, skipUnlessPathExists

SCRIPT_CONTENT = """#!/bin/bash
/bin/sleep 30
"""


class TaskTimeOutTest(TestCaseTmpDir):

    def setUp(self):
        super().setUp()
        self.script = script.TemporaryScript(
            'sleep.sh',
            SCRIPT_CONTENT,
            'avocado_timeout_functional')
        self.script.save()

    @skipUnlessPathExists('/bin/sleep')
    def test_sleep_longer_timeout(self):
        config = {'resolver.references': [self.script.path],
                  'run.results_dir': self.tmpdir.name,
                  'task.timeout.running': 2,
                  'run.test_runner': 'nrunner'}

        with Job.from_config(job_config=config) as job:
            job.run()

        self.assertEqual(1, job.result.skipped)
        self.assertEqual(0, job.result.passed)

    def tearDown(self):
        super().tearDown()
        self.script.remove()
