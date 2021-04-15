"""
Functional tests for features available through the job API
"""

import os
import unittest

from avocado.core import exit_codes
from avocado.core.job import Job
from selftests.utils import TestCaseTmpDir


class Test(TestCaseTmpDir):

    def setUp(self):
        super(Test, self).setUp()
        self.base_config = {'core.show': ['none'],
                            'run.results_dir': self.tmpdir.name,
                            'run.references': ['examples/tests/passtest.py'],
                            'run.keep_tmp': True}

    def test_job_run_result_json_enabled(self):
        self.base_config['job.run.result.json.enabled'] = True
        j = Job.from_config(self.base_config)
        j.setup()
        result = j.run()
        self.assertEqual(result, exit_codes.AVOCADO_ALL_OK)
        json_results_path = os.path.join(self.tmpdir.name, 'latest', 'results.json')
        self.assertTrue(os.path.exists(json_results_path))

    def test_job_run_result_json_output(self):
        json_results_path = os.path.join(self.tmpdir.name, 'myresults.json')
        self.base_config['job.run.result.json.output'] = json_results_path
        j = Job.from_config(self.base_config)
        j.setup()
        result = j.run()
        self.assertEqual(result, exit_codes.AVOCADO_ALL_OK)
        self.assertTrue(os.path.exists(json_results_path))


if __name__ == '__main__':
    unittest.main()
