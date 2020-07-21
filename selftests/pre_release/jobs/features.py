#!/usr/bin/env python3

import os

from avocado import Test
from avocado.core import exit_codes
from avocado.core.job import Job

BOOLEAN_ENABLED = 'on'
BOOLEAN_DISABLED = 'off'


class JobAPIFeaturesTest(Test):

    def check_exit_code(self, exit_code):
        """Check if job ended with success"""
        expected_exit_code = self.params.get('exit_code',
                                             default=exit_codes.AVOCADO_ALL_OK)
        self.assertEqual(expected_exit_code, exit_code)

    def check_file_exists(self, file_path, value):
        """Check if a file exist or not depending on the `assert_func`"""
        assert_func = self.get_assert_function(value)
        assert_func(os.path.exists(file_path))

    def check_file_content(self, file_path, value):
        """Check if `content` exists or not in a file."""
        content = self.params.get('content')
        assert_func = self.get_assert_function(value)
        assert_func(self.file_has_content(file_path, content))

    @staticmethod
    def file_has_content(file_path, content):
        """Check if a file has `content`."""
        if os.path.isfile(file_path):
            with open(file_path, "r") as f:
                source_content = f.read()
            if content in source_content:
                return True
        return False

    def get_assert_function(self, value):
        """Return an assert function depending on the value passed"""
        if value == BOOLEAN_ENABLED:
            assert_func = self.assertTrue
        else:
            assert_func = self.assertFalse
        return assert_func

    @property
    def result_file_path(self):
        file_name = self.params.get('file')
        return os.path.join(self.workdir, 'latest', file_name)

    def test_check_file(self):
        """Test to check if a file was created."""

        config = {'core.show': ['none'],
                  'run.results_dir': self.workdir,
                  'run.references': ['/bin/true']}
        namespace = self.params.get('namespace')
        value = self.params.get('value')
        config[namespace] = value

        # run the job
        with Job(config) as j:
            result = j.run()

        # Asserts
        self.check_exit_code(result)
        self.check_file_exists(self.result_file_path, value)

    def test_check_content(self):
        """Test to check if a file has the desired content."""

        config = {'core.show': ['none'],
                  'run.results_dir': self.workdir,
                  'run.references': ['/bin/true']}
        namespace = self.params.get('namespace')
        value = self.params.get('value')
        config[namespace] = value

        # run the job
        with Job(config) as j:
            result = j.run()

        # Asserts
        self.check_exit_code(result)
        self.check_file_content(self.result_file_path, value)


if __name__ == '__main__':

    #DIR = os.path.dirname(os.path.abspath(__file__))

    # First test with its config
    reference = '%s:JobAPIFeaturesTest.test_check_file' % __file__
    config = {'run.references': [reference],
              'run.dict_variants': [

                  {'namespace': 'job.run.result.html.enabled',
                   'file': 'results.html',
                   'value': 'on'},

                  {'namespace': 'job.run.result.html.enabled',
                   'file': 'results.html',
                   'value': 'off'},

                  {'namespace': 'job.run.result.json.enabled',
                   'file': 'results.json',
                   'value': 'on'},

                  {'namespace': 'job.run.result.json.enabled',
                   'file': 'results.json',
                   'value': 'off'},

                  {'namespace': 'job.run.result.tap.enabled',
                   'file': 'results.tap',
                   'value': 'on'},

                  {'namespace': 'job.run.result.tap.enabled',
                   'file': 'results.tap',
                   'value': 'off'},

                  {'namespace': 'job.run.result.xunit.enabled',
                   'file': 'results.xml',
                   'value': 'on'},

                  {'namespace': 'job.run.result.xunit.enabled',
                   'file': 'results.xml',
                   'value': 'off'},

              ]}

    with Job(config) as j:
        j.run()

    # Second test with its config
    reference = '%s:JobAPIFeaturesTest.test_check_content' % __file__
    config = {'run.references': [reference],
              'run.dict_variants': [

                  {'namespace': 'job.run.result.tap.include_logs',
                   'file': 'results.tap',
                   'content': "Command '/bin/true' finished with 0",
                   'value': 'on'},

                  {'namespace': 'job.run.result.tap.include_logs',
                   'file': 'results.tap',
                   'content': "Command '/bin/true' finished with 0",
                   'value': 'off'},

              ]}

    with Job(config) as j:
        j.run()
