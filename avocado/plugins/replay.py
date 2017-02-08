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
# Copyright: Red Hat Inc. 2016
# Author: Amador Pahim <apahim@redhat.com>

import argparse
import json
import logging
import os
import sys

from avocado.core import exit_codes
from avocado.core import jobdata
from avocado.core import status

from avocado.core.plugin_interfaces import CLI
from avocado.core.settings import settings
from avocado.core.test import ReplaySkipTest


class Replay(CLI):

    """
    Replay a job
    """

    name = 'replay'
    description = "Replay options for 'run' subcommand"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        msg = 'job replay'
        replay_parser = run_subcommand_parser.add_argument_group(msg)
        replay_parser.add_argument('--replay', dest='replay_jobid',
                                   default=None,
                                   help='Replay a job identified by its '
                                   '(partial) hash id. Use "--replay latest" '
                                   'to replay the latest job.')
        replay_parser.add_argument('--replay-test-status',
                                   dest='replay_teststatus',
                                   type=self._valid_status,
                                   default=None,
                                   help='Filter tests to replay by '
                                   'test status')
        replay_parser.add_argument('--replay-ignore',
                                   dest='replay_ignore',
                                   type=self._valid_ignore,
                                   default=[],
                                   help='Ignore variants (variants) and/or '
                                   'configuration (config) from the '
                                   'source job')

    def _valid_status(self, string):
        status_list = string.split(',')
        for item in status_list:
            if item not in status.user_facing_status:
                msg = ('Invalid --replay-test-status option. Valid '
                       'options are (more than one allowed): %s' %
                       ','.join([item for item in status.user_facing_status]))
                raise argparse.ArgumentTypeError(msg)

        return status_list

    def _valid_ignore(self, string):
        options = ['variants', 'config']
        ignore_list = string.split(',')
        for item in ignore_list:
            if item not in options:
                msg = ('Invalid --replay-ignore option. Valid '
                       'options are (more than one allowed): %s'
                       % ','.join(options))
                raise argparse.ArgumentTypeError(msg)

        return ignore_list

    def load_config(self, resultsdir):
        config = jobdata.retrieve_config(resultsdir)
        if config is not None:
            settings.process_config_path(config)

    def _create_replay_map(self, resultsdir, replay_filter):
        """
        Creates a mapping to be used as filter for the replay. Given
        the replay_filter, tests that should be filtered out will have a
        correspondent ReplaySkipTest class in the map. Tests that should
        be replayed will have a correspondent None in the map.
        """
        json_results = os.path.join(resultsdir, "results.json")
        if not os.path.exists(json_results):
            return None

        with open(json_results, 'r') as json_file:
            results = json.loads(json_file.read())

        replay_map = []
        for test in results['tests']:
            if test['status'] not in replay_filter:
                replay_map.append(ReplaySkipTest)
            else:
                replay_map.append(None)

        return replay_map

    def run(self, args):
        if getattr(args, 'replay_jobid', None) is None:
            return

        log = logging.getLogger("avocado.app")

        err = None
        if args.replay_teststatus and 'variants' in args.replay_ignore:
            err = ("Option `--replay-test-status` is incompatible with "
                   "`--replay-ignore variants`.")
        elif args.replay_teststatus and args.reference:
            err = ("Option --replay-test-status is incompatible with "
                   "test references given on the command line.")
        elif args.remote_hostname:
            err = "Currently we don't replay jobs in remote hosts."
        if err is not None:
            log.error(err)
            sys.exit(exit_codes.AVOCADO_FAIL)

        if getattr(args, 'logdir', None) is not None:
            logdir = args.logdir
        else:
            logdir = settings.get_value(section='datadir.paths',
                                        key='logs_dir', key_type='path',
                                        default=None)
        try:
            resultsdir = jobdata.get_resultsdir(logdir, args.replay_jobid)
        except ValueError as exception:
            log.error(exception.message)
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)

        if resultsdir is None:
            log.error("Can't find job results directory in '%s'", logdir)
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)

        sourcejob = jobdata.get_id(os.path.join(resultsdir, 'id'),
                                   args.replay_jobid)
        if sourcejob is None:
            msg = ("Can't find matching job id '%s' in '%s' directory."
                   % (args.replay_jobid, resultsdir))
            log.error(msg)
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)
        setattr(args, 'replay_sourcejob', sourcejob)

        replay_args = jobdata.retrieve_args(resultsdir)
        whitelist = ['loaders',
                     'external_runner',
                     'external_runner_testdir',
                     'external_runner_chdir',
                     'failfast']
        if replay_args is None:
            log.warn('Source job args data not found. These options will not '
                     'be loaded in this replay job: %s', ', '.join(whitelist))
        else:
            for option in whitelist:
                optvalue = getattr(args, option, None)
                if optvalue is not None:
                    log.warn("Overriding the replay %s with the --%s value "
                             "given on the command line.",
                             option.replace('_', '-'),
                             option.replace('_', '-'))
                else:
                    setattr(args, option, replay_args[option])

        # Keeping this for compatibility.
        # TODO: Use replay_args['reference'] at some point in the future.
        if getattr(args, 'reference', None):
            log.warn('Overriding the replay test references with test '
                     'references given in the command line.')
        else:
            references = jobdata.retrieve_references(resultsdir)
            if references is None:
                log.error('Source job test references data not found. Aborting.')
                sys.exit(exit_codes.AVOCADO_JOB_FAIL)
            else:
                setattr(args, 'reference', references)

        if 'config' in args.replay_ignore:
            log.warn("Ignoring configuration from source job with "
                     "--replay-ignore.")
        else:
            self.load_config(resultsdir)

        if 'variants' in args.replay_ignore:
            log.warn("Ignoring variants from source job with "
                     "--replay-ignore.")
        else:
            variants = jobdata.retrieve_variants(resultsdir)
            if variants is None:
                log.error('Source job variants data not found. Aborting.')
                sys.exit(exit_codes.AVOCADO_JOB_FAIL)
            else:
                # Ignore data manipulation. This is necessary, because
                # we replaced the unparsed object with parsed one. There
                # are other plugins running before/after this which might
                # want to alter the variants object.
                if args.avocado_variants.is_parsed():
                    log.warning("Using src job Mux data only, use `--replay-"
                                "ignore variants` to override them.")
                setattr(args, "avocado_variants", variants)
                variants.ignore_new_data = True

        if args.replay_teststatus:
            replay_map = self._create_replay_map(resultsdir,
                                                 args.replay_teststatus)
            setattr(args, 'replay_map', replay_map)

        # Use the original directory to resolve test references properly
        pwd = jobdata.retrieve_pwd(resultsdir)
        if pwd is not None:
            if os.path.exists(pwd):
                os.chdir(pwd)
            else:
                log.warn("Directory used in the replay source job '%s' does "
                         "not exist, using '.' instead", pwd)
