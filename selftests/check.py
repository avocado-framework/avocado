#!/usr/bin/env python3

import argparse
import glob
import multiprocessing
import os
import platform
import re
import sys

from avocado import Test
from avocado.core import exit_codes
from avocado.core.job import Job
from avocado.core.suite import TestSuite
from selftests.utils import python_module_available


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
        regex = self.params.get('regex', default=False)
        assert_func(self.file_has_content(file_path, content, regex))

    def create_config(self, value=None):
        """Creates the Job config."""
        if value is None:
            value = self.params.get('value')
        reference = self.params.get('reference', default=['/bin/true'])
        config = {'core.show': ['none'],
                  'run.results_dir': self.workdir,
                  'resolver.references': reference}
        namespace = self.params.get('namespace')
        config[namespace] = value
        extra_job_config = self.params.get('extra_job_config')
        if extra_job_config is not None:
            config.update(extra_job_config)

        return config

    @staticmethod
    def file_has_content(file_path, content, regex):
        """Check if a file has `content`."""
        if os.path.isfile(file_path):
            with open(file_path, "r") as f:
                lines = f.readlines()
            for line in lines:
                if regex:
                    if re.match(content, line):
                        return True
                else:
                    if content in line:
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

        suite = TestSuite.from_config(config, '')

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
                        '--list-features',
                        help='show the list of features tested by this test.',
                        action='store_true')
    parser.add_argument('--static-checks',
                        help='Run static checks (isort, lint, etc)',
                        action='store_true')
    parser.add_argument('--job-api',
                        help='Run job API checks',
                        action='store_true')
    parser.add_argument('--nrunner-interface',
                        help='Run selftests/functional/test_nrunner_interface.py',
                        action='store_true')
    parser.add_argument('--unit',
                        help='Run selftests/unit/',
                        action='store_true')
    parser.add_argument('--jobs',
                        help='Run selftests/jobs/',
                        action='store_true')
    parser.add_argument('--functional',
                        help='Run selftests/functional/',
                        action='store_true')
    parser.add_argument('--optional-plugins',
                        help='Run optional_plugins/*/tests/',
                        action='store_true')
    parser.add_argument('--disable-plugin-checks',
                        help='Disable checks for one or more plugins (by directory name), separated by comma',
                        action='append', default=[])

    arg = parser.parse_args()
    # Make a list of strings instead of a list with a single string
    if len(arg.disable_plugin_checks) > 0:
        arg.disable_plugin_checks = arg.disable_plugin_checks[0].split(",")
    return arg


def create_suite_job_api(args):  # pylint: disable=W0621
    suites = []

    def get_ref(method_short_name):
        return ['%s:JobAPIFeaturesTest.test_%s' % (__file__, method_short_name)]

    # ========================================================================
    # Test if the archive file was created
    # ========================================================================
    config_check_archive_file_exists = {
        'resolver.references': get_ref('check_archive_file_exists'),
        'run.dict_variants.variant_id_keys': ['namespace', 'value'],
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
    config_check_category_directory_exists = {
        'resolver.references': get_ref('check_category_directory_exists'),
        'run.dict_variants.variant_id_keys': ['namespace', 'value'],
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
    config_check_directory_exists = {
        'resolver.references': get_ref('check_directory_exists'),
        'run.dict_variants.variant_id_keys': ['namespace', 'value'],
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
    config_check_file_content = {
        'resolver.references': get_ref('check_file_content'),
        'run.dict_variants.variant_id_keys': ['namespace', 'value', 'file'],
        'run.dict_variants': [
            # finding the correct 'content' here is trick because any
            # simple string is added to the variant file name and is
            # found in the log file.
            # Using DEBUG| makes the variant name have DEBUG_, working
            # fine here.
            {'namespace': 'job.output.loglevel',
             'value': 'INFO',
             'file': 'job.log',
             'content': r'DEBUG\| Test metadata:$',
             'assert': False,
             'regex': True},

            {'namespace': 'job.run.result.tap.include_logs',
             'value': True,
             'file': 'results.tap',
             'reference': ['examples/tests/passtest.py:PassTest.test'],
             'content': 'PASS 1-examples/tests/passtest.py:PassTest.test',
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
             'reference': ['examples/tests/failtest.py:FailTest.test'],
             'exit_code': 1},

            {'namespace': 'run.failfast',
             'value': True,
             'file': 'results.json',
             'content': '"skip": 1',
             'assert': True,
             'reference': ['/bin/false', '/bin/true'],
             'exit_code': 9,
             'extra_job_config': {'nrunner.max_parallel_tasks': 1}},

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
    config_check_file_exists = {
        'resolver.references': get_ref('check_file_exists'),
        'run.dict_variants.variant_id_keys': ['namespace', 'value'],
        'run.dict_variants': [
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

    if (python_module_available('avocado-framework-plugin-result-html') and
            'html' not in args.disable_plugin_checks):

        config_check_file_exists['run.dict_variants'].append(
            {'namespace': 'job.run.result.html.enabled',
             'value': True,
             'file': 'results.html',
             'assert': True})

        config_check_file_exists['run.dict_variants'].append(
            {'namespace': 'job.run.result.html.enabled',
             'value': False,
             'file': 'results.html',
             'assert': False})

    suites.append(TestSuite.from_config(config_check_file_exists,
                                        "job-api-%s" % (len(suites) + 1)))

    # ========================================================================
    # Test if a file was created
    # ========================================================================
    config_check_output_file = {
        'resolver.references': get_ref('check_output_file'),
        'run.dict_variants.variant_id_keys': ['namespace', 'file'],
        'run.dict_variants': [
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

    if (python_module_available('avocado-framework-plugin-result-html') and
            'html' not in args.disable_plugin_checks):

        config_check_output_file['run.dict_variants'].append(
            {'namespace': 'job.run.result.html.output',
             'file': 'custom.html',
             'assert': True})

    suites.append(TestSuite.from_config(config_check_output_file,
                                        "job-api-%s" % (len(suites) + 1)))

    # ========================================================================
    # Test if the temporary directory was created
    # ========================================================================
    config_check_tmp_directory_exists = {
        'resolver.references': get_ref('check_tmp_directory_exists'),
        'run.dict_variants.variant_id_keys': ['namespace', 'value'],
        'run.dict_variants': [
            {'namespace': 'run.keep_tmp',
             'value': True,
             'assert': True},
        ]
    }

    suites.append(TestSuite.from_config(config_check_tmp_directory_exists,
                                        "job-api-%s" % (len(suites) + 1)))
    return suites


def create_suites(args):  # pylint: disable=W0621
    suites = []
    # ========================================================================
    # Run nrunner interface checks for all available runners
    # ========================================================================
    config_nrunner_interface = {
        'resolver.references': ['selftests/functional/test_nrunner_interface.py'],
        'run.dict_variants.variant_id_keys': ['runner'],
        'run.dict_variants': [
            {'runner': 'avocado-runner',
             'runnable-run-no-args-exit-code': 2,
             'runnable-run-uri-only-exit-code': 2},

            {'runner': 'avocado-runner-noop',
             'runnable-run-no-args-exit-code': 0,
             'runnable-run-uri-only-exit-code': 0},

            {'runner': 'avocado-runner-exec-test',
             'runnable-run-no-args-exit-code': 0,
             'runnable-run-uri-only-exit-code': 0},

            {'runner': 'avocado-runner-python-unittest',
             'runnable-run-no-args-exit-code': 0,
             'runnable-run-uri-only-exit-code': 0},

            {'runner': 'avocado-runner-avocado-instrumented',
             'runnable-run-no-args-exit-code': 0,
             'runnable-run-uri-only-exit-code': 0},

            {'runner': 'avocado-runner-tap',
             'runnable-run-no-args-exit-code': 0,
             'runnable-run-uri-only-exit-code': 0},
        ]
    }

    if (python_module_available('avocado-framework-plugin-golang') and
            'golang' not in args.disable_plugin_checks):
        config_nrunner_interface['run.dict_variants'].append({
            'runner': 'avocado-runner-golang',
            'runnable-run-no-args-exit-code': 0,
            'runnable-run-uri-only-exit-code': 0})

    if (python_module_available('avocado-framework-plugin-robot') and
            'robot' not in args.disable_plugin_checks):
        config_nrunner_interface['run.dict_variants'].append({
            'runner': 'avocado-runner-robot',
            'runnable-run-no-args-exit-code': 0,
            'runnable-run-uri-only-exit-code': 0})

    if args.nrunner_interface:
        suites.append(TestSuite.from_config(config_nrunner_interface, "nrunner-interface"))

    # ========================================================================
    # Run all static checks, unit and functional tests
    # ========================================================================

    selftests = []
    if args.unit:
        selftests.append('selftests/unit/')
    if args.jobs:
        selftests.append('selftests/jobs/')
    if args.functional:
        selftests.append('selftests/functional/')

    config_check = {
        'resolver.references': selftests,
        'run.ignore_missing_references': True
    }

    if args.static_checks:
        config_check['resolver.references'] += glob.glob('selftests/*.sh')

    if args.optional_plugins:
        for optional_plugin in glob.glob('optional_plugins/*'):
            plugin_name = os.path.basename(optional_plugin)
            if plugin_name not in args.disable_plugin_checks:
                pattern = '%s/tests/*' % optional_plugin
                config_check['resolver.references'] += glob.glob(pattern)

    suites.append(TestSuite.from_config(config_check, "check"))

    return suites


def print_failed_tests(tests):
    if tests:
        print("Failed tests:")
        for test in tests:
            print(test.get('name'), test.get('status'))


def enable_all_tests(args):   # pylint: disable=W0621
    args.static_checks = True
    args.job_api = True
    args.nrunner_interface = True
    args.unit = True
    args.jobs = True
    args.functional = True
    args.optional_plugins = True


def main(args):  # pylint: disable=W0621

    # ========================================================================
    # Print features covered in this test
    # ========================================================================
    if args.list_features:
        suites = create_suite_job_api(args)
        suites += create_suites(args)
        features = []
        for suite in suites:
            for variants in suite.config['run.dict_variants']:
                if variants.get('namespace'):
                    features.append(variants['namespace'])

        unique_features = sorted(set(features))
        print('Features covered (%i):' % len(unique_features))
        print('\n'.join(unique_features))
        exit(0)

    if not any([args.static_checks, args.job_api, args.nrunner_interface,
                args.unit, args.jobs, args.functional,
                args.optional_plugins, args.list_features]):
        print("No test were selected to run, running all of them.")
        enable_all_tests(args)

    suites = []
    if args.job_api:
        suites += create_suite_job_api(args)
    suites += create_suites(args)

    # ========================================================================
    # Job execution
    # ========================================================================
    config = {'core.show': ['app'],
              'run.job_category': 'avocado-selftests',
              'job.output.testlogs.statuses': ['FAIL', 'ERROR', 'INTERRUPT'],
              'job.output.testlogs.logfiles': ['debug.log']}

    # Workaround for travis problem on arm64 - https://github.com/avocado-framework/avocado/issues/4768
    if (platform.machine() == 'aarch64'):
        max_parallel = int(multiprocessing.cpu_count()/2)
        for suite in suites:
            if suite.name == 'check':
                suite.config['nrunner.max_parallel_tasks'] = max_parallel

    with Job(config, suites) as j:
        exit_code = j.run()
    print_failed_tests(j.get_failed_tests())
    return exit_code


if __name__ == '__main__':
    args = parse_args()
    sys.exit(main(args))
