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

from avocado.core import exit_codes
from avocado.core import job
from avocado.core import loader
from avocado.core import output
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.dispatcher import ResultDispatcher
from avocado.core.dispatcher import JobPrePostDispatcher
from avocado.core.settings import settings
from avocado.utils.data_structures import time_to_seconds
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

        parser.add_argument("reference", type=str, default=[], nargs='*',
                            metavar="TEST_REFERENCE",
                            help='List of test references (aliases or paths)')

        parser.add_argument("-p", "--test-parameter", action="append",
                            dest='test_parameters', default=[],
                            metavar="NAME_VALUE", type=self._test_parameter,
                            help="Parameter name and value to pass to all "
                            "tests. This is only applicable when not using a "
                            "varianter plugin. This option format must be "
                            "given in the NAME=VALUE format, and may be given "
                            "any number of times, or per parameter.")

        parser.add_argument("-d", "--dry-run", action="store_true",
                            help="Instead of running the test only "
                            "list them and log their params.")

        parser.add_argument("--dry-run-no-cleanup", action="store_true",
                            help="Do not automatically clean up temporary "
                            "directories used by dry-run", default=False)

        parser.add_argument('--force-job-id', dest='unique_job_id',
                            type=str, default=None,
                            help='Forces the use of a particular job ID. Used '
                            'internally when interacting with an avocado '
                            'server. You should not use this option '
                            'unless you know exactly what you\'re doing')

        parser.add_argument('--job-results-dir', action='store',
                            dest='base_logdir', default=None, metavar='DIRECTORY',
                            help=('Forces to use of an alternate job '
                                  'results directory.'))

        parser.add_argument('--job-timeout', action='store',
                            default=None, metavar='SECONDS',
                            help='Set the maximum amount of time (in SECONDS) '
                            'that tests are allowed to execute. '
                            'Values <= zero means "no timeout". '
                            'You can also use suffixes, like: '
                            ' s (seconds), m (minutes), h (hours). ')

        parser.add_argument('--failfast', choices=('on', 'off'),
                            help='Enable or disable the job interruption on '
                            'first failed test.')

        parser.add_argument('--keep-tmp', choices=('on', 'off'),
                            default='off', help='Keep job temporary files '
                            '(useful for avocado debugging). Defaults to off.')

        parser.add_argument('--ignore-missing-references', choices=('on', 'off'),
                            help="Force the job execution, even if some of "
                            "the test references are not resolved to tests.")

        sysinfo_default = settings.get_value('sysinfo.collect',
                                             'enabled',
                                             key_type='bool',
                                             default=True)
        sysinfo_default = 'on' if sysinfo_default is True else 'off'
        parser.add_argument('--sysinfo', choices=('on', 'off'),
                            default=sysinfo_default, help="Enable or disable "
                            "system information (hardware details, profilers, "
                            "etc.). Current:  %(default)s")

        parser.add_argument("--execution-order",
                            choices=("tests-per-variant",
                                     "variants-per-test"),
                            help="Defines the order of iterating through test "
                            "suite and test variants")

        parser.output = parser.add_argument_group('output and result format')

        parser.output.add_argument('-s', '--silent', action="store_true",
                                   default=argparse.SUPPRESS,
                                   help='Silence stdout')

        parser.output.add_argument('--show-job-log', action='store_true',
                                   default=False, help="Display only the job "
                                   "log on stdout. Useful for test debugging "
                                   "purposes. No output will be displayed if "
                                   "you also specify --silent")

        parser.output.add_argument("--store-logging-stream", nargs="*",
                                   default=[], metavar="STREAM[:LEVEL]",
                                   help="Store given logging STREAMs in "
                                   "$JOB_RESULTS_DIR/$STREAM.$LEVEL.")

        parser.output.add_argument("--log-test-data-directories",
                                   action="store_true",
                                   help="Logs the possible data directories "
                                   "for each test. This is helpful when "
                                   "writing new tests and not being sure "
                                   "where to put data files. Look for \""
                                   "Test data directories\" in your test log")

        out_check = parser.add_argument_group('output check arguments')

        out_check.add_argument('--output-check-record',
                               choices=('none', 'stdout', 'stderr',
                                        'both', 'combined', 'all'),
                               help="Record the output produced by each test "
                                    "(from stdout and stderr) into both the "
                                    "current executing result and into  "
                                    "reference files.  Reference files are "
                                    "used on subsequent runs to determine if "
                                    "the test produced the expected output or "
                                    "not, and the current executing result is "
                                    "used to check against a previously "
                                    "recorded reference file.  Valid values: "
                                    "'none' (to explicitly disable all "
                                    "recording) 'stdout' (to record standard "
                                    "output *only*), 'stderr' (to record "
                                    "standard error *only*), 'both' (to record"
                                    " standard output and error in separate "
                                    "files), 'combined' (for standard output "
                                    "and error in a single file). 'all' is "
                                    "also a valid but deprecated option that "
                                    "is a synonym of 'both'.  This option "
                                    "does not have a default value, but the "
                                    "Avocado test runner will record the "
                                    "test under execution in the most suitable"
                                    " way unless it's explicitly disabled with"
                                    " value 'none'")

        out_check.add_argument('--output-check', choices=('on', 'off'),
                               default='on',
                               help="Enable or disable test output (stdout/"
                               "stderr) check. If this option is off, no "
                               "output will be checked, even if there are "
                               "reference files present for the test. "
                               "Current: on (output check enabled)")

        loader.add_loader_options(parser)

        filtering = parser.add_argument_group('filtering parameters')
        filtering.add_argument('-t', '--filter-by-tags', metavar='TAGS',
                               action='append',
                               help='Filter INSTRUMENTED tests based on '
                               '":avocado: tags=tag1,tag2" notation in '
                               'their class docstring')
        filtering.add_argument('--filter-by-tags-include-empty',
                               action='store_true', default=False,
                               help=('Include all tests without tags during '
                                     'filtering. This effectively means they '
                                     'will be kept in the test suite found '
                                     'previously to filtering.'))

    def run(self, args):
        """
        Run test modules or simple tests.

        :param args: Command line args received from the run subparser.
        """
        if 'output_check_record' in args:
            process.OUTPUT_CHECK_RECORD_MODE = getattr(args,
                                                       'output_check_record',
                                                       None)

        if args.unique_job_id is not None:
            try:
                int(args.unique_job_id, 16)
                if len(args.unique_job_id) != 40:
                    raise ValueError
            except ValueError:
                LOG_UI.error('Unique Job ID needs to be a 40 digit hex number')
                sys.exit(exit_codes.AVOCADO_FAIL)
        try:
            args.job_timeout = time_to_seconds(args.job_timeout)
        except ValueError as detail:
            LOG_UI.error(detail.args[0])
            sys.exit(exit_codes.AVOCADO_FAIL)
        with job.Job(args) as job_instance:
            pre_post_dispatcher = JobPrePostDispatcher()
            try:
                # Run JobPre plugins
                output.log_plugin_failures(pre_post_dispatcher.load_failures)
                pre_post_dispatcher.map_method('pre', job_instance)

                job_run = job_instance.run()
            finally:
                # Run JobPost plugins
                pre_post_dispatcher.map_method('post', job_instance)

            result_dispatcher = ResultDispatcher()
            if result_dispatcher.extensions:
                result_dispatcher.map_method('render',
                                             job_instance.result,
                                             job_instance)
        return job_run
