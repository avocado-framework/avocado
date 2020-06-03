"""
Functional tests for features available through the job API
"""

import os
import tempfile
import unittest

from .. import temp_dir_prefix

from avocado.core.job import Job
from avocado.core import exit_codes


class Test(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)
        self.base_config = {'core.show': ['none'],
                            'run.results_dir': self.tmpdir.name,
                            'run.references': ['examples/tests/passtest.py']}

    def test_job_run_result_json_enabled(self):
        self.base_config['job.run.result.json.enabled'] = 'on'
        with Job(self.base_config) as j:
            result = j.run()
        self.assertEqual(result, exit_codes.AVOCADO_ALL_OK)
        json_results_path = os.path.join(self.tmpdir.name, 'latest', 'results.json')
        self.assertTrue(os.path.exists(json_results_path))

    def test_job_run_result_json_output(self):
        json_results_path = os.path.join(self.tmpdir.name, 'myresults.json')
        self.base_config['job.run.result.json.output'] = json_results_path
        with Job(self.base_config) as j:
            result = j.run()
        self.assertEqual(result, exit_codes.AVOCADO_ALL_OK)
        self.assertTrue(os.path.exists(json_results_path))

    def tearDown(self):
        self.tmpdir.cleanup()


if __name__ == '__main__':
    unittest.main()
