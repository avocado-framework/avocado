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
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

import argparse
import logging
import os
import sys

from .base import CLI
from avocado.core import replay
from avocado.core import status
from avocado.core import exit_codes
from avocado.core.settings import settings


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
                                   '(partial) hash id')
        replay_parser.add_argument('--replay-test-status',
                                   dest='replay_teststatus',
                                   type=self._valid_status,
                                   default=None,
                                   help='Filter tests to replay by '
                                   'test status')
        replay_parser.add_argument('--replay-ignore',
                                   dest='replay_ignore',
                                   type=self._valid_ignore,
                                   default=None,
                                   help='Ignore multiplex (mux) and/or '
                                   'configuration (config) from the '
                                   'source job')
        replay_parser.add_argument('--replay-data-dir',
                                   dest='replay_datadir',
                                   default=None,
                                   help='Load replay data from an '
                                   'alternative location')

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
        options = ['mux', 'config']
        ignore_list = string.split(',')
        for item in ignore_list:
            if item not in options:
                msg = ('Invalid --replay-ignore option. Valid '
                       'options are (more than one allowed): %s'
                       % ','.join(options))
                raise argparse.ArgumentTypeError(msg)

        return ignore_list

    def load_config(self, resultsdir):
        config = os.path.join(resultsdir, 'replay', 'config')
        with open(config, 'r') as f:
            settings.process_config_path(f.read())

    def run(self, args):
        if getattr(args, 'replay_jobid', None) is None:
            return

        log = logging.getLogger("avocado.app")

        err = None
        if args.replay_teststatus and args.multiplex_files:
            err = ("Option --replay-test-status is incompatible with "
                   "--multiplex.")
        elif args.replay_teststatus and args.url:
            err = ("Option --replay-test-status is incompatible with "
                   "test URLs given on the command line.")
        elif args.remote_hostname:
            err = "Currently we don't replay jobs in remote hosts."
        if err is not None:
            log.error(err)
            sys.exit(exit_codes.AVOCADO_FAIL)

        if args.replay_datadir is not None:
            resultsdir = args.replay_datadir
        else:
            logs_dir = settings.get_value('datadir.paths', 'logs_dir',
                                          default=None)
            logdir = os.path.expanduser(logs_dir)
            resultsdir = replay.get_resultsdir(logdir, args.replay_jobid)

        if resultsdir is None:
            log.error("Can't find job results directory in '%s'", logdir)
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)

        sourcejob = replay.get_id(os.path.join(resultsdir, 'id'),
                                  args.replay_jobid)
        if sourcejob is None:
            msg = ("Can't find matching job id '%s' in '%s' directory."
                   % (args.replay_jobid, resultsdir))
            log.error(msg)
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)
        setattr(args, 'replay_sourcejob', sourcejob)

        replay_args = replay.retrieve_args(resultsdir)
        whitelist = ['loaders',
                     'external_runner',
                     'external_runner_testdir',
                     'external_runner_chdir']
        if replay_args is None:
            log.warn('Source job args data not found. These options will not '
                     'be loaded in this replay job: %s', ', '.join(whitelist))
        else:
            for option in whitelist:
                optvalue = getattr(args, option, None)
                if optvalue:
                    log.warn("Overriding the replay %s with the --%s value "
                             "given on the command line.",
                             option.replace('_', '-'),
                             option.replace('_', '-'))
                else:
                    setattr(args, option, replay_args[option])

        # Keeping this for compatibility.
        # TODO: Use replay_args['url'] at some point in the future.
        if getattr(args, 'url', None):
            log.warn('Overriding the replay urls with urls provided in '
                     'command line.')
        else:
            urls = replay.retrieve_urls(resultsdir)
            if urls is None:
                log.error('Source job urls data not found. Aborting.')
                sys.exit(exit_codes.AVOCADO_JOB_FAIL)
            else:
                setattr(args, 'url', urls)

        if args.replay_ignore and 'config' in args.replay_ignore:
            log.warn("Ignoring configuration from source job with "
                     "--replay-ignore.")
        else:
            self.load_config(resultsdir)

        if args.replay_ignore and 'mux' in args.replay_ignore:
            log.warn("Ignoring multiplex from source job with "
                     "--replay-ignore.")
        else:
            if getattr(args, 'multiplex_files', None) is not None:
                log.warn('Overriding the replay multiplex with '
                         '--multiplex-file.')
                # Use absolute paths to avoid problems with os.chdir
                args.multiplex_files = [os.path.abspath(_)
                                        for _ in args.multiplex_files]
            else:
                mux = replay.retrieve_mux(resultsdir)
                if mux is None:
                    log.error('Source job multiplex data not found. Aborting.')
                    sys.exit(exit_codes.AVOCADO_JOB_FAIL)
                else:
                    setattr(args, "multiplex_files", mux)

        if args.replay_teststatus:
            replay_map = replay.retrieve_replay_map(resultsdir,
                                                    args.replay_teststatus)
            setattr(args, 'replay_map', replay_map)

        # Use the original directory to discover test urls properly
        pwd = replay.retrieve_pwd(resultsdir)
        if pwd is not None:
            if os.path.exists(pwd):
                os.chdir(pwd)
            else:
                log.warn("Directory used in the replay source job '%s' does "
                         "not exist, using '.' instead", pwd)
