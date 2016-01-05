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

import os
import sys

from .base import CLI
from avocado.core import replay
from avocado.core import exit_codes
from avocado.core import output
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
        self.replay_parser = run_subcommand_parser.add_argument_group(msg)
        self.replay_parser.add_argument('--replay', dest='replay_jobid',
                                        default=None,
                                        help='Replay a job identified by its '
                                        '(partial) hash id')
        self.replay_parser.add_argument('--replay-test-status',
                                        dest='replay_teststatus',
                                        default=None,
                                        help='Filter tests to replay by '
                                        'test status')
        self.replay_parser.add_argument('--replay-ignore',
                                        dest='replay_ignore',
                                        default=None,
                                        help='Ignore multiplex (mux) and/or '
                                        'configuration (config) from the '
                                        'source job')
        self.replay_parser.add_argument('--replay-data-dir',
                                        dest='replay_datadir',
                                        default=None,
                                        help='Load replay data from an '
                                        'alternative location')

    def _check_args(self, args):
        view = output.View()
        valid_ignore = frozenset(['config', 'mux'])
        valid_status = frozenset(['FAIL', 'PASS', 'ERROR', 'SKIP', 'WARN',
                                 'INTERRUPT'])

        replay_teststatus = getattr(args, 'replay_teststatus')
        replay_ignore = getattr(args, 'replay_ignore')

        resultsdir = getattr(args, 'replay_resultsdir')
        if resultsdir is None:
            msg = 'Job data not found in %s. Please make sure you\'re '\
                  'informing a valid and unique enough hash.' % self.logdir
            view.notify(event='error', msg=(msg))
            return sys.exit(exit_codes.AVOCADO_JOB_FAIL)

        if replay_teststatus is not None:
            for item in replay_teststatus.split(','):
                if item not in valid_status:
                    e_msg = 'Invalid --replay-test-status option. Valid ' \
                            'options are (more than one allowed): %s' % \
                            ','.join(valid_status)
                    view.notify(event='error', msg=e_msg)
                    return sys.exit(exit_codes.AVOCADO_FAIL)

        if replay_ignore is not None:
            for item in replay_ignore.split(','):
                if item not in valid_ignore:
                    e_msg = 'Invalid --replay-ignore option. Valid ' \
                            'options are (more than one allowed): %s' % \
                            ','.join(valid_ignore)
                    view.notify(event='error', msg=e_msg)
                    return sys.exit(exit_codes.AVOCADO_FAIL)
                if item == 'config':
                    msg = '* Ignoring configuration from source job.'
                    view.notify(event='warning', msg=(msg))
                elif item == 'mux':
                    msg = '* Ignoring multiplex-files from source job.'
                    view.notify(event='warning', msg=(msg))

        return True

    def _load_config(self, args):
        replay_ignore = getattr(args, 'replay_ignore')
        if replay_ignore is None or 'config' not in replay_ignore.split(','):
            replay_config = os.path.join(getattr(args, 'replay_resultsdir'),
                                         'replay', 'config')
            with open(replay_config, 'r') as f:
                settings.process_config_path(f.read())

    def run(self, args):
        replay_jobid = getattr(args, 'replay_jobid')
        replay_datadir = getattr(args, 'replay_datadir')
        if replay_datadir is not None:
            self.logdir = os.path.expanduser(replay_datadir)
        else:
            logs_dir = settings.get_value('datadir.paths', 'logs_dir',
                                          default=None)
            self.logdir = os.path.expanduser(logs_dir)

        resultsdir, sourcejob = replay.get_resultsdir(self.logdir,
                                                      replay_jobid)
        setattr(args, 'replay_resultsdir', resultsdir)
        setattr(args, 'replay_sourcejob', sourcejob)

        if self._check_args(args):
            self._load_config(args)
