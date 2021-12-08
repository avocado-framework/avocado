# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2013-2014
# Author: Ruda Moura <rmoura@redhat.com>

"""
Base Test Runner Plugins.
"""

import argparse
import sys

from avocado.core import exit_codes, job, loader, parser_common_args
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd, Init
from avocado.core.settings import settings
from avocado.core.suite import TestSuite, TestSuiteError


class RunInit(Init):

    name = 'run'
    description = 'Initializes the run options'

    def initialize(self):
        help_msg = ('Defines the order of iterating through test suite '
                    'and test variants')
        settings.register_option(section='run',
                                 key='execution_order',
                                 choices=('tests-per-variant',
                                          'variants-per-test'),
                                 default='variants-per-test',
                                 help_msg=help_msg)


class Run(CLICmd):

    """
    Implements the avocado 'run' subcommand
    """

    name = 'run'
    description = ("Runs one or more tests (native test, test alias, binary "
                   "or script)")

    @staticmethod
    def _test_parameter(string):
        param_name_value = string.split('=', 1)
        if len(param_name_value) < 2:
            msg = ('Invalid --test-parameter option: "%s". Valid option must '
                   'be a "NAME=VALUE" like expression' % string)
            raise argparse.ArgumentTypeError(msg)
        return param_name_value

    def configure(self, parser):
        """
        Add the subparser for the run action.

        :param parser: Main test runner parser.
        """
        parser = super(Run, self).configure(parser)

        settings.add_argparser_to_option(namespace='resolver.references',
                                         nargs='*',
                                         metavar='TEST_REFERENCE',
                                         parser=parser,
                                         positional_arg=True,
                                         long_arg=None,
                                         allow_multiple=True)

        help_msg = ('Parameter name and value to pass to all tests. This is '
                    'only applicable when not using a varianter plugin. '
                    'This option format must be given in the NAME=VALUE '
                    'format, and may be given any number of times, or per '
                    'parameter.')
        settings.register_option(section='run',
                                 key='test_parameters',
                                 action='append',
                                 default=[],
                                 key_type=self._test_parameter,
                                 metavar="NAME_VALUE",
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--test-parameter',
                                 short_arg='-p')

        settings.add_argparser_to_option(namespace='run.test_runner',
                                         parser=parser,
                                         long_arg='--test-runner',
                                         metavar='TEST_RUNNER')

        help_msg = ('Instead of running the test only list them and log '
                    'their params.')
        settings.register_option(section='run.dry_run',
                                 key='enabled',
                                 default=False,
                                 key_type=bool,
                                 help_msg=help_msg,
                                 parser=parser,
                                 short_arg='-d',
                                 long_arg='--dry-run')

        help_msg = ('Do not automatically clean up temporary directories '
                    'used by dry-run')
        settings.register_option(section='run.dry_run',
                                 key='no_cleanup',
                                 help_msg=help_msg,
                                 default=False,
                                 key_type=bool,
                                 parser=parser,
                                 long_arg='--dry-run-no-cleanup')

        help_msg = ('Forces the use of a particular job ID. Used internally '
                    'when interacting with an avocado server. You should not '
                    'use this option unless you know exactly what you\'re '
                    'doing')
        settings.register_option(section='run',
                                 key='unique_job_id',
                                 default=None,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--force-job-id',
                                 metavar='UNIQUE_JOB_ID')

        help_msg = 'Forces to use of an alternate job results directory.'
        settings.register_option(section='run',
                                 key='results_dir',
                                 default=None,
                                 metavar='DIRECTORY',
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--job-results-dir')

        help_msg = ('Categorizes this within a directory with the same name, '
                    'by creating a link to the job result directory')
        settings.register_option(section='run',
                                 key='job_category',
                                 help_msg=help_msg,
                                 parser=parser,
                                 default=None,
                                 metavar='CATEGORY',
                                 long_arg='--job-category')

        settings.add_argparser_to_option(namespace='job.run.timeout',
                                         metavar='SECONDS',
                                         parser=parser,
                                         long_arg='--job-timeout')

        help_msg = 'Enable the job interruption on first failed test.'
        settings.register_option(section='run',
                                 key='failfast',
                                 default=False,
                                 key_type=bool,
                                 action='store_true',
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--failfast')

        help_msg = 'Keep job temporary files (useful for avocado debugging).'
        settings.register_option(section='run',
                                 key='keep_tmp',
                                 default=False,
                                 key_type=bool,
                                 action='store_true',
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--keep-tmp')

        help_msg = ('Force the job execution, even if some of the test '
                    'references are not resolved to tests.')
        settings.register_option(section='run',
                                 key='ignore_missing_references',
                                 default=False,
                                 key_type=bool,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--ignore-missing-references')

        settings.add_argparser_to_option(namespace='sysinfo.collect.enabled',
                                         parser=parser,
                                         action='store_false',
                                         long_arg='--disable-sysinfo')

        settings.add_argparser_to_option('run.execution_order',
                                         parser=parser,
                                         long_arg='--execution-order')

        parser.output = parser.add_argument_group('output and result format')

        settings.add_argparser_to_option('job.run.store_logging_stream',
                                         parser=parser.output,
                                         long_arg='--store-logging-stream',
                                         metavar='LOGGING_STREAM',
                                         argparse_type=lambda x: set(x.split(',')))

        help_msg = ('Logs the possible data directories for each test. This '
                    'is helpful when writing new tests and not being sure '
                    'where to put data files. Look for "Test data '
                    'directories" in your test log')
        settings.register_option(section='run',
                                 key='log_test_data_directories',
                                 default=False,
                                 key_type=bool,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--log-test-data-directories')

        loader.add_loader_options(parser, 'run')
        parser_common_args.add_tag_filter_args(parser)

    def run(self, config):
        """
        Run test modules or simple tests.

        :param config: Configuration received from command line parser and
                       possibly other sources.
        :type config: dict
        """
        unique_job_id = config.get('run.unique_job_id')
        if unique_job_id is not None:
            try:
                int(unique_job_id, 16)
                if len(unique_job_id) != 40:
                    raise ValueError
            except ValueError:
                LOG_UI.error('Unique Job ID needs to be a 40 digit hex number')
                sys.exit(exit_codes.AVOCADO_FAIL)

        try:
            suite = TestSuite.from_config(config, name='')
            if suite.size == 0:
                msg = ("Suite is empty. There is no tests to run. This usually "
                       "happens when you pass --ignore-missing-references and "
                       "there is no more references to process.")
                LOG_UI.warning(msg)
                sys.exit(exit_codes.AVOCADO_FAIL)
        except TestSuiteError as err:
            LOG_UI.error(err)
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)
        with job.Job(config, [suite]) as job_instance:
            return job_instance.run()
