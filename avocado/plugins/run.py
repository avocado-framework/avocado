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
import warnings

from avocado.core import exit_codes
from avocado.core import job
from avocado.core import loader
from avocado.core import output
from avocado.core import parser_common_args
from avocado.core.dispatcher import JobPrePostDispatcher
from avocado.core.future.settings import settings
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.utils import process


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

        help_msg = 'List of test references (aliases or paths)'
        settings.register_option(section='run',
                                 key='references',
                                 key_type=list,
                                 default=[],
                                 nargs='*',
                                 metavar='TEST_REFERENCE',
                                 parser=parser,
                                 help_msg=help_msg,
                                 positional_arg=True)

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

        help_msg = ('Selects the runner implementation from one of the '
                    'installed and active implementations.  You can run '
                    '"avocado plugins" and find the list of valid runners '
                    'under the "Plugins that run test suites on a job '
                    '(runners) section.  Defaults to "runner", which is '
                    'the conventional and traditional runner.')
        settings.register_option(section='run',
                                 key='test_runner',
                                 default='runner',
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--test-runner')

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
                                 long_arg='--force-job-id')

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

        help_msg = ('Set the maximum amount of time (in SECONDS) that tests '
                    'are allowed to execute. Values <= zero means "no '
                    'timeout". You can also use suffixes, like: s (seconds), '
                    'm (minutes), h (hours). ')
        settings.register_option(section='run',
                                 key='job_timeout',
                                 help_msg=help_msg,
                                 default='0',
                                 metavar='SECONDS',
                                 parser=parser,
                                 long_arg='--job-timeout')

        help_msg = ('Enable or disable the job interruption on first failed '
                    'test. "on" and "off" will be deprecated soon.')
        settings.register_option(section='run',
                                 key='failfast',
                                 choices=('on', 'off'),
                                 default='off',
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--failfast')

        help_msg = ('Keep job temporary files (useful for avocado debugging). '
                    '"on" and "off" will be deprecated soon.')
        settings.register_option(section='run',
                                 key='keep_tmp',
                                 choices=('on', 'off'),
                                 default='off',
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--keep-tmp')

        help_msg = ('Force the job execution, even if some of the test '
                    'references are not resolved to tests. "on" and '
                    '"off" will be deprecated soon.')
        settings.register_option(section='run',
                                 key='ignore_missing_references',
                                 default=False,
                                 key_type=bool,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--ignore-missing-references')

        settings.add_argparser_to_option(namespace='sysinfo.collect.enabled',
                                         parser=parser,
                                         choices=('on', 'off'),
                                         short_arg='-S',
                                         long_arg='--sysinfo')

        help_msg = ('Defines the order of iterating through test suite '
                    'and test variants')
        settings.register_option(section='run',
                                 key='execution_order',
                                 choices=('tests-per-variant',
                                          'variants-per-test'),
                                 default=None,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--execution-order')

        parser.output = parser.add_argument_group('output and result format')

        help_msg = ('Store given logging STREAMs in '
                    '"$JOB_RESULTS_DIR/$STREAM.$LEVEL."')
        settings.register_option(section='run',
                                 key='store_logging_stream',
                                 nargs='*',
                                 help_msg=help_msg,
                                 default=[],
                                 metavar='STREAM[:LEVEL]',
                                 key_type=list,
                                 parser=parser,
                                 long_arg='--store-logging-stream')

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

        out_check = parser.add_argument_group('output check arguments')

        help_msg = ('Record the output produced by each test (from stdout '
                    'and stderr) into both the current executing result '
                    'and into reference files. Reference files are used on '
                    'subsequent runs to determine if the test produced the '
                    'expected output or not, and the current executing result '
                    'is used to check against a previously recorded reference '
                    'file.  Valid values: "none" (to explicitly disable all '
                    'recording) "stdout" (to record standard output *only*), '
                    '"stderr" (to record standard error *only*), "both" (to '
                    'record standard output and error in separate files), '
                    '"combined" (for standard output and error in a single '
                    'file). "all" is also a valid but deprecated option that '
                    'is a synonym of "both".')
        settings.register_option(section='run',
                                 key='output_check_record',
                                 help_msg=help_msg,
                                 choices=('none', 'stdout', 'stderr',
                                          'both', 'combined', 'all'),
                                 parser=parser,
                                 default=None,
                                 long_arg='--output-check-record')

        help_msg = ('Enable or disable test output (stdout/stderr) check. If '
                    'this option is off, no output will be checked, even if '
                    'there are reference files present for the test. "on" '
                    'and "off" will be deprecated soon.')
        settings.register_option(section='run',
                                 key='output_check',
                                 default='on',
                                 choices=('on', 'off'),
                                 help_msg=help_msg,
                                 parser=out_check,
                                 long_arg='--output-check')

        loader.add_loader_options(parser, 'run')
        parser_common_args.add_tag_filter_args(parser)

    def run(self, config):
        """
        Run test modules or simple tests.

        :param config: Configuration received from command line parser and
                       possibly other sources.
        :type config: dict
        """
        if 'run.output_check_record' in config:
            check_record = config.get('run.output_check_record')
            process.OUTPUT_CHECK_RECORD_MODE = check_record

        warnings.warn("The following arguments will be changed to boolean soon: "
                      "sysinfo, output-check, failfast and keep-tmp. ",
                      FutureWarning)

        unique_job_id = config.get('run.unique_job_id')
        if unique_job_id is not None:
            try:
                int(unique_job_id, 16)
                if len(unique_job_id) != 40:
                    raise ValueError
            except ValueError:
                LOG_UI.error('Unique Job ID needs to be a 40 digit hex number')
                sys.exit(exit_codes.AVOCADO_FAIL)

        with job.Job(config) as job_instance:
            pre_post_dispatcher = JobPrePostDispatcher()
            try:
                # Run JobPre plugins
                output.log_plugin_failures(pre_post_dispatcher.load_failures)
                pre_post_dispatcher.map_method('pre', job_instance)

                job_run = job_instance.run()
            finally:
                # Run JobPost plugins
                pre_post_dispatcher.map_method('post', job_instance)

        return job_run
