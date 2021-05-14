#!/usr/bin/env python3

import argparse
import glob
import os
import sys

from avocado import Test
from avocado.core import exit_codes
from avocado.core.job import Job
from avocado.core.suite import TestSuite
from avocado.utils.network.ports import find_free_port

BOOLEAN_ENABLED = [True, 'true', 'on', 1]
BOOLEAN_DISABLED = [False, 'false', 'off', 0]


class JobAPIFeaturesTest(Test):

    def check_directory_exists(self, path=None):
        """Check if a directory exists"""
        if path is None:
            path = os.path.join(self.latest_workdir,
                                self.params.get('directory'))
        assert_func = self.get_assert_function()
        assert_func(os.path.isdir(path))

    def check_exit_code(self, exit_code):
        """Check if job ended with success."""
        expected_exit_code = self.params.get('exit_code',
                                             default=exit_codes.AVOCADO_ALL_OK)
        self.assertEqual(expected_exit_code, exit_code)

    def check_file_exists(self, file_path):
        """Check if a file exists or not depending on the `assert_func`."""
        assert_func = self.get_assert_function()
        assert_func(os.path.exists(file_path))

    def check_file_content(self, file_path):
        """Check if `content` exists or not in a file."""
        content = self.params.get('content')
        assert_func = self.get_assert_function()
        assert_func(self.file_has_content(file_path, content))

    def create_config(self, value=None):
        """Creates the Job config."""
        if value is None:
            value = self.params.get('value')
        reference = self.params.get('reference', default=['/bin/true'])
        config = {'core.show': ['none'],
                  'run.results_dir': self.workdir,
                  'run.references': reference}
        namespace = self.params.get('namespace')
        config[namespace] = value

        return config

    @staticmethod
    def file_has_content(file_path, content):
        """Check if a file has `content`."""
        if os.path.isfile(file_path):
            with open(file_path, "r") as f:
                source_content = f.read()
            if content in source_content:
                return True
        return False

    def get_assert_function(self):
        """Return an assert function depending on the assert passed"""
        assert_option = self.params.get('assert')
        if assert_option:
            return self.assertTrue
        return self.assertFalse

    @property
    def latest_workdir(self):
        return os.path.join(self.workdir, 'latest')

    def run_job(self):
        """Run a Job"""
        config = self.create_config()

        suite = TestSuite.from_config(config)

        # run the job
        with Job(config, [suite]) as j:
            result = j.run()

        return result

    @property
    def workdir_file_path(self):
        file_name = self.params.get('file')
        return os.path.join(self.latest_workdir, file_name)

    def test_check_archive_file_exists(self):
        """Test to check the archive file was created."""
        config = self.create_config()

        suite = TestSuite.from_config(config)

        # run the job
        with Job(config, [suite]) as j:
            result = j.run()
            logdir = j.logdir

        # Asserts
        self.check_exit_code(result)
        archive_path = '%s.zip' % logdir
        self.check_file_exists(archive_path)

    def test_check_category_directory_exists(self):
        """Test to check if the category directory was created."""
        config = self.create_config()

        suite = TestSuite.from_config(config)

        # run the job
        with Job(config, [suite]) as j:
            result = j.run()
            logdir = j.logdir

        # Asserts
        self.check_exit_code(result)

        value = self.params.get('value')
        category_path = os.path.join(os.path.dirname(logdir), value)
        self.check_directory_exists(category_path)

    def test_check_directory_exists(self):
        """Test to check if a directory was created."""
        config = self.create_config()

        suite = TestSuite.from_config(config)

        # run the job
        with Job(config, [suite]) as j:
            result = j.run()

        # Asserts
        self.check_exit_code(result)
        self.check_directory_exists()

    def test_check_file_content(self):
        """Test to check if a file has the desired content."""
        result = self.run_job()

        # Asserts
        self.check_exit_code(result)
        self.check_file_content(self.workdir_file_path)

    def test_check_file_exists(self):
        """Test to check if a file was created."""
        result = self.run_job()

        # Asserts
        self.check_exit_code(result)
        self.check_file_exists(self.workdir_file_path)

    def test_check_output_file(self):
        """Test to check if the file passed as parameter was created."""
        config = self.create_config(self.workdir_file_path)

        suite = TestSuite.from_config(config)

        # run the job
        with Job(config, [suite]) as j:
            result = j.run()

        # Asserts
        self.check_exit_code(result)
        self.check_file_exists(self.workdir_file_path)

    def test_check_tmp_directory_exists(self):
        """Test to check if the temporary directory was created."""
        config = self.create_config()

        suite = TestSuite.from_config(config)

        # run the job
        with Job(config, [suite]) as j:
            result = j.run()
            tmpdir = j.tmpdir

        # Asserts
        self.check_exit_code(result)
        self.check_directory_exists(tmpdir)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f',
                        '--features',
                        help='show the features tested by this test.',
                        action='store_true')
    parser.add_argument('--disable-static-checks',
                        help='Disable the static checks (isort, lint, etc)',
                        action='store_true')
    parser.add_argument('--disable-plugin-checks',
                        help='Disable checks for a plugin (by directory name)',
                        action='append', default=[])
    return parser.parse_args()


def create_suites(args):
    test_class = 'JobAPIFeaturesTest'
    suites = []

    # ========================================================================
    # Test if the archive file was created
    # ========================================================================
    check_archive_file_exists = ('%s:%s.test_check_archive_file_exists'
                                 % (__file__, test_class))
    config_check_archive_file_exists = {
        'run.references': [check_archive_file_exists],
        'run.test_runner': 'runner',
        'run.dict_variants': [
            {'namespace': 'run.results.archive',
             'value': True,
             'assert': True},
        ]
    }

    suites.append(TestSuite.from_config(config_check_archive_file_exists,
                                        "job-api-%s" % (len(suites) + 1)))

    # ========================================================================
    # Test if the category directory was created
    # ========================================================================
    check_category_directory_exists = (
        '%s:%s.test_check_category_directory_exists'
        % (__file__, test_class))
    config_check_category_directory_exists = {
        'run.references': [check_category_directory_exists],
        'run.test_runner': 'runner',
        'run.dict_variants': [
            {'namespace': 'run.job_category',
             'value': 'foo',
             'assert': True},
        ]
    }

    suites.append(TestSuite.from_config(config_check_category_directory_exists,
                                        "job-api-%s" % (len(suites) + 1)))

    # ========================================================================
    # Test if a directory was created
    # ========================================================================
    check_directory_exists = ('%s:%s.test_check_directory_exists'
                              % (__file__, test_class))
    config_check_directory_exists = {
        'run.references': [check_directory_exists],
        'run.test_runner': 'runner',
        'run.dict_variants': [
             {'namespace': 'sysinfo.collect.enabled',
              'value': True,
              'directory': 'sysinfo',
              'assert': True},

             {'namespace': 'sysinfo.collect.enabled',
              'value': False,
              'directory': 'sysinfo',
              'assert': False},
        ]
    }

    suites.append(TestSuite.from_config(config_check_directory_exists,
                                        "job-api-%s" % (len(suites) + 1)))

    # ========================================================================
    # Test the content of a file
    # ========================================================================
    check_file_content = ('%s:%s.test_check_file_content'
                          % (__file__, test_class))
    config_check_file_content = {
        'run.references': [check_file_content],
        'run.test_runner': 'runner',
        'run.dict_variants': [
            # finding the correct 'content' here is trick because any
            # simple string is added to the variant file name and is
            # found in the log file.
            # Using DEBUG| makes the variant name have DEBUG_, working
            # fine here.
            {'namespace': 'job.output.loglevel',
             'value': 'INFO',
             'file': 'job.log',
             'content': 'DEBUG| Test metadata',
             'assert': False},

            {'namespace': 'job.run.result.tap.include_logs',
             'value': True,
             'file': 'results.tap',
             'content': "Command '/bin/true' finished with 0",
             'assert': True},

            {'namespace': 'job.run.result.tap.include_logs',
             'value': False,
             'file': 'results.tap',
             'content': "Command '/bin/true' finished with 0",
             'assert': False},

            {'namespace': 'job.run.result.xunit.job_name',
             'value': 'foo',
             'file': 'results.xml',
             'content': 'name="foo"',
             'assert': True},

            {'namespace': 'job.run.result.xunit.max_test_log_chars',
             'value': 1,
             'file': 'results.xml',
             'content': '--[ CUT DUE TO XML PER TEST LIMIT ]--',
             'assert': True,
             'reference': ['/bin/false'],
             'exit_code': 1},

            {'namespace': 'run.failfast',
             'value': True,
             'file': 'results.json',
             'content': '"skip": 1',
             'assert': True,
             'reference': ['/bin/false', '/bin/true'],
             'exit_code': 9},

            {'namespace': 'run.ignore_missing_references',
             'value': 'on',
             'file': 'results.json',
             'content': '"pass": 1',
             'assert': True,
             'reference': ['/bin/true', 'foo']},

            {'namespace': 'run.unique_job_id',
             'value': 'abcdefghi',
             'file': 'job.log',
             'content': 'Job ID: abcdefghi',
             'assert': True},

            {'namespace': 'job.run.timeout',
             'value': 1,
             'reference': ['examples/tests/sleeptenmin.py'],
             'file': 'job.log',
             'content': 'RuntimeError: Test interrupted by SIGTERM',
             'assert': True,
             'exit_code': 8},
        ]
    }

    suites.append(TestSuite.from_config(config_check_file_content,
                                        "job-api-%s" % (len(suites) + 1)))

    # ========================================================================
    # Test if the result file was created
    # ========================================================================
    check_file_exists = ('%s:%s.test_check_file_exists'
                         % (__file__, test_class))
    config_check_file_exists = {
        'run.references': [check_file_exists],
        'run.test_runner': 'runner',
        'run.dict_variants': [
            {'namespace': 'job.run.result.html.enabled',
             'value': True,
             'file': 'results.html',
             'assert': True},

            {'namespace': 'job.run.result.html.enabled',
             'value': False,
             'file': 'results.html',
             'assert': False},

            {'namespace': 'job.run.result.json.enabled',
             'value': True,
             'file': 'results.json',
             'assert': True},

            {'namespace': 'job.run.result.json.enabled',
             'value': False,
             'file': 'results.json',
             'assert': False},

            {'namespace': 'job.run.result.tap.enabled',
             'value': True,
             'file': 'results.tap',
             'assert': True},

            {'namespace': 'job.run.result.tap.enabled',
             'value': False,
             'file': 'results.tap',
             'assert': False},

            {'namespace': 'job.run.result.xunit.enabled',
             'value': True,
             'file': 'results.xml',
             'assert': True},

            {'namespace': 'job.run.result.xunit.enabled',
             'value': False,
             'file': 'results.xml',
             'assert': False},

            {'namespace': 'run.dry_run.enabled',
             'value': True,
             'file': 'job.log',
             'assert': False},

            {'namespace': 'run.dry_run.no_cleanup',
             'value': True,
             'file': 'job.log',
             'assert': True},

            {'namespace': 'plugins.disable',
             'value': ['result.xunit'],
             'file': 'result.xml',
             'assert': False},

            # this test needs a huge improvement
            {'namespace': 'run.journal.enabled',
             'value': True,
             'file': '.journal.sqlite',
             'assert': True},
        ]
    }

    suites.append(TestSuite.from_config(config_check_file_exists,
                                        "job-api-%s" % (len(suites) + 1)))

    # ========================================================================
    # Test if a file was created
    # ========================================================================
    check_output_file = ('%s:%s.test_check_output_file'
                         % (__file__, test_class))
    config_check_output_file = {
        'run.references': [check_output_file],
        'run.test_runner': 'runner',
        'run.dict_variants': [
            {'namespace': 'job.run.result.html.output',
             'file': 'custom.html',
             'assert': True},

            {'namespace': 'job.run.result.json.output',
             'file': 'custom.json',
             'assert': True},

            # https://github.com/avocado-framework/avocado/issues/4034
            {'namespace': 'job.run.result.tap.output',
             'file': 'custom.tap',
             'assert': True},

            {'namespace': 'job.run.result.xunit.output',
             'file': 'custom.xml',
             'assert': True},
        ]
    }

    suites.append(TestSuite.from_config(config_check_output_file,
                                        "job-api-%s" % (len(suites) + 1)))

    # ========================================================================
    # Test if the temporary directory was created
    # ========================================================================
    check_tmp_directory_exists = ('%s:%s.test_check_tmp_directory_exists'
                                  % (__file__, test_class))
    config_check_tmp_directory_exists = {
        'run.references': [check_tmp_directory_exists],
        'run.test_runner': 'runner',
        'run.dict_variants': [
            {'namespace': 'run.keep_tmp',
             'value': True,
             'assert': True},
        ]
    }

    suites.append(TestSuite.from_config(config_check_tmp_directory_exists,
                                        "job-api-%s" % (len(suites) + 1)))

    # ========================================================================
    # Run nrunner interface checks for all available runners
    # ========================================================================
    config_nrunner_interface = {
        'run.references': ['selftests/functional/test_nrunner_interface.py'],
        'run.dict_variants': [
            {'runner': 'avocado-runner'},
            {'runner': 'avocado-runner-noop'},
            {'runner': 'avocado-runner-exec'},
            {'runner': 'avocado-runner-exec-test'},
            {'runner': 'avocado-runner-python-unittest'},
            {'runner': 'avocado-runner-avocado-instrumented'},
            {'runner': 'avocado-runner-tap'},
            {'runner': 'avocado-runner-golang'}
        ]
    }

    if 'robot' not in args.disable_plugin_checks:
        config_nrunner_interface['run.dict_variants'].append({
            'runner': 'avocado-runner-robot'})

    suites.append(TestSuite.from_config(config_nrunner_interface,
                                        "nrunner-interface"))

    # ========================================================================
    # Run all static checks, unit and functional tests
    # ========================================================================
    status_server = '127.0.0.1:%u' % find_free_port()
    config_check = {
        'run.references': ['selftests/jobs/',
                           'selftests/unit/',
                           'selftests/functional/'],
        'run.test_runner': 'nrunner',
        'nrunner.status_server_listen': status_server,
        'nrunner.status_server_uri': status_server,
        'run.ignore_missing_references': True,
        'job.output.testlogs.statuses': ['FAIL']
    }

    if not args.disable_static_checks:
        config_check['run.references'] += glob.glob('selftests/*.sh')

    for optional_plugin in glob.glob('optional_plugins/*'):
        plugin_name = os.path.basename(optional_plugin)
        if plugin_name not in args.disable_plugin_checks:
            pattern = '%s/tests/*' % optional_plugin
            config_check['run.references'] += glob.glob(pattern)

    suites.append(TestSuite.from_config(config_check, "check"))
    return suites


def print_failed_tests(tests):
    if tests:
        print("Failed tests:")
        for test in tests:
            print(test.get('name'), test.get('status'))


def main():
    args = parse_args()
    suites = create_suites(args)
    # ========================================================================
    # Print features covered in this test
    # ========================================================================
    if args.features:
        features = []
        for suite in suites:
            for variants in suite.config['run.dict_variants']:
                features.append(variants['namespace'])

        unique_features = sorted(set(features))
        print('Features covered (%i):' % len(unique_features))
        print('\n'.join(unique_features))
        exit(0)

    # ========================================================================
    # Job execution
    # ========================================================================
    config = {'core.show': ['app'],
              'run.test_runner': 'nrunner'}
    with Job(config, suites) as j:
        exit_code = j.run()
    print_failed_tests(j.get_failed_tests())
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
