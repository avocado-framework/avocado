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
import logging
import sys

from avocado.core import exit_codes
from avocado.core import job
from avocado.core import loader
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.dispatcher import ResultDispatcher
from avocado.core.settings import settings
from avocado.utils.data_structures import time_to_seconds


class Run(CLICmd):

    """
    Implements the avocado 'run' subcommand
    """

    name = 'run'
    description = ("Runs one or more tests (native test, test alias, binary"
                   "or script)")

    def configure(self, parser):
        """
        Add the subparser for the run action.

        :param parser: Main test runner parser.
        """
        parser = super(Run, self).configure(parser)

        parser.add_argument("url", type=str, default=[], nargs='*',
                            metavar="TEST_REFERENCE",
                            help='List of test references (aliases or paths)')

        parser.add_argument("-d", "--dry-run", action="store_true",
                            help="Instead of running the test only "
                            "list them and log their params.")

        parser.add_argument('-z', '--archive', action='store_true',
                            default=False, help='Archive (ZIP) files generated'
                            ' by tests')

        parser.add_argument('--force-job-id', dest='unique_job_id',
                            type=str, default=None,
                            help='Forces the use of a particular job ID. Used '
                            'internally when interacting with an avocado '
                            'server. You should not use this option '
                            'unless you know exactly what you\'re doing')

        parser.add_argument('--job-results-dir', action='store',
                            dest='logdir', default=None, metavar='DIRECTORY',
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

        sysinfo_default = settings.get_value('sysinfo.collect',
                                             'enabled',
                                             key_type='bool',
                                             default=True)
        sysinfo_default = 'on' if sysinfo_default is True else 'off'
        parser.add_argument('--sysinfo', choices=('on', 'off'),
                            default=sysinfo_default, help="Enable or disable "
                            "system information (hardware details, profilers, "
                            "etc.). Current:  %(default)s")

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

        out_check = parser.add_argument_group('output check arguments')

        out_check.add_argument('--output-check-record',
                               choices=('none', 'all', 'stdout', 'stderr'),
                               default='none',
                               help="Record output streams of your tests "
                               "to reference files (valid options: none (do "
                               "not record output streams), all (record both "
                               "stdout and stderr), stdout (record only "
                               "stderr), stderr (record only stderr). "
                               'Current: %(default)s')

        out_check.add_argument('--output-check', choices=('on', 'off'),
                               default='on',
                               help="Enable or disable test output (stdout/"
                               "stderr) check. If this option is off, no "
                               "output will be checked, even if there are "
                               "reference files present for the test. "
                               "Current: on (output check enabled)")

        loader.add_loader_options(parser)

        mux = parser.add_argument_group('test parameters')
        mux.add_argument('--filter-only', nargs='*', default=[],
                         help='Filter only path(s) from multiplexing')
        mux.add_argument('--filter-out', nargs='*', default=[],
                         help='Filter out path(s) from multiplexing')
        mux.add_argument('--mux-path', nargs='*', default=None,
                         help="List of paths used to determine path "
                         "priority when querying for parameters")
        mux.add_argument('--mux-inject', default=[], nargs='*',
                         help="Inject [path:]key:node values into the "
                         "final multiplex tree.")

    def run(self, args):
        """
        Run test modules or simple tests.

        :param args: Command line args received from the run subparser.
        """
        log = logging.getLogger("avocado.app")
        if args.unique_job_id is not None:
            try:
                int(args.unique_job_id, 16)
                if len(args.unique_job_id) != 40:
                    raise ValueError
            except ValueError:
                log.error('Unique Job ID needs to be a 40 digit hex number')
                sys.exit(exit_codes.AVOCADO_FAIL)
        try:
            args.job_timeout = time_to_seconds(args.job_timeout)
        except ValueError as e:
            log.error(e.message)
            sys.exit(exit_codes.AVOCADO_FAIL)
        job_instance = job.Job(args)
        job_run = job_instance.run()
        result_dispatcher = ResultDispatcher()
        if result_dispatcher.extensions:
            # At this point job_instance doesn't have a single results
            # attribute which is the end goal.  For now, we pick any of the
            # plugin classes added to the result proxy.
            if len(job_instance.result_proxy.output_plugins) > 0:
                result = job_instance.result_proxy.output_plugins[0]
                result_dispatcher.map_method('render', result, job_instance)
        return job_run
