#!/usr/bin/env python3

import os
import sys
import time

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

    def check_file_exists(self, file_path, assert_func):
        """Check if a file exist or not depending on the `assert_func`"""
        assert_func(os.path.exists(file_path))

    def check_file_content(self, file_path, assert_func, content):
        """
        Check if `content` exist or not in a file depending on the
        `assert_func`
        """
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

        self.check_exit_code(result)

        assert_func = self.get_assert_function(value)
        self.check_file_exists(self.result_file_path, assert_func)

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

        self.check_exit_code(result)

        assert_func = self.get_assert_function(value)
        content = self.params.get('content')
        self.check_file_content(self.result_file_path, assert_func, content)


if __name__ == '__main__':

    DIR = os.path.dirname(os.path.abspath(__file__))

    # First test with its config
    reference = '%s:JobAPIFeaturesTest.test_check_file' % __file__
    config = {'run.references': [reference],
              'yaml_to_mux.files': [
                  os.path.join(DIR,
                               'yaml',
                               'check_file_features.yaml')]
              }

    with Job(config) as j:
        j.run()

    # Second test with its config
    reference = '%s:JobAPIFeaturesTest.test_check_content' % __file__
    config = {'run.references': [reference],
              'yaml_to_mux.files': [
                  os.path.join(DIR,
                               'yaml',
                               'check_content_features.yaml')]
              }

    with Job(config) as j:
        j.run()
