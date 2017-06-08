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
import os
import re
import sys

from avocado.core import exit_codes
from avocado.core import jobdata
from avocado.core import status

from avocado.core.output import LOG_UI
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
        replay_parser.add_argument("--replay-resume", action="store_true",
                                   help="Resume an interrupted job")

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

    def _get_tests_from_tap(self, path):
        if not os.path.exists(path):
            return None
        re_result = re.compile(r"(not )?ok (\d+) ([^#]*)(# (\w+).*)?")
        re_no_tests = re.compile(r"1..(\d+)")
        max_index = 0
        no_tests = 0
        _tests = {}
        for line in open(path):
            line = line.strip()
            if line.startswith("#"):
                continue
            result = re_result.match(line)
            if result:
                if result.group(1) is None:
                    res = result.group(5)
                    if res is None:
                        res = "PASS"
                else:
                    res = "ERROR"
                index = int(result.group(2))
                _tests[index] = {"status": res,
                                 "test": result.group(3).rstrip()}
                max_index = max(max_index, index)
                continue
            _no_tests = re_no_tests.match(line)
            if _no_tests:
                no_tests = int(_no_tests.group(1))
                continue

        if not (no_tests or max_index):
            return None

        # Now add _tests that were not executed
        skipped_test = {"test": "UNKNOWN", "status": "INTERRUPTED"}
        return [_tests[i] if i in _tests else skipped_test
                for i in xrange(1, max(max_index, no_tests) + 1)]

    def _create_replay_map(self, resultsdir, replay_filter):
        """
        Creates a mapping to be used as filter for the replay. Given
        the replay_filter, tests that should be filtered out will have a
        correspondent ReplaySkipTest class in the map. Tests that should
        be replayed will have a correspondent None in the map.
        """
        json_results = os.path.join(resultsdir, "results.json")
        if os.path.exists(json_results):
            with open(json_results, 'r') as json_file:
                results = json.loads(json_file.read())
                tests = results["tests"]
                for _ in xrange(results["total"] + 1 - len(tests)):
                    tests.append({"test": "UNKNOWN", "status": "INTERRUPTED"})
        else:
            # get partial results from tap
            tests = self._get_tests_from_tap(os.path.join(resultsdir,
                                                          "results.tap"))
            if not tests:   # tests not available, ignore replay map
                return None

        replay_map = []
        for test in tests:
            if test['status'] not in replay_filter:
                replay_map.append(ReplaySkipTest)
            else:
                replay_map.append(None)

        return replay_map

    def run(self, args):
        if getattr(args, 'replay_jobid', None) is None:
            return

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
            LOG_UI.error(err)
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
            LOG_UI.error(exception.message)
            sys.exit(exit_codes.AVOCADO_FAIL)

        if resultsdir is None:
            LOG_UI.error("Can't find job results directory in '%s'", logdir)
            sys.exit(exit_codes.AVOCADO_FAIL)

        sourcejob = jobdata.get_id(os.path.join(resultsdir, 'id'),
                                   args.replay_jobid)
        if sourcejob is None:
            msg = ("Can't find matching job id '%s' in '%s' directory."
                   % (args.replay_jobid, resultsdir))
            LOG_UI.error(msg)
            sys.exit(exit_codes.AVOCADO_FAIL)
        setattr(args, 'replay_sourcejob', sourcejob)

        replay_args = jobdata.retrieve_args(resultsdir)
        whitelist = ['loaders',
                     'external_runner',
                     'external_runner_testdir',
                     'external_runner_chdir',
                     'failfast',
                     'ignore_missing_references']
        if replay_args is None:
            LOG_UI.warn('Source job args data not found. These options will '
                        'not be loaded in this replay job: %s',
                        ', '.join(whitelist))
        else:
            for option in whitelist:
                optvalue = getattr(args, option, None)
                if optvalue is not None:
                    LOG_UI.warn("Overriding the replay %s with the --%s value "
                                "given on the command line.",
                                option.replace('_', '-'),
                                option.replace('_', '-'))
                else:
                    setattr(args, option, replay_args[option])

        # Keeping this for compatibility.
        # TODO: Use replay_args['reference'] at some point in the future.
        if getattr(args, 'reference', None):
            LOG_UI.warn('Overriding the replay test references with test '
                        'references given in the command line.')
        else:
            references = jobdata.retrieve_references(resultsdir)
            if references is None:
                LOG_UI.error('Source job test references data not found. '
                             'Aborting.')
                sys.exit(exit_codes.AVOCADO_FAIL)
            else:
                setattr(args, 'reference', references)

        if 'config' in args.replay_ignore:
            LOG_UI.warn("Ignoring configuration from source job with "
                        "--replay-ignore.")
        else:
            self.load_config(resultsdir)

        if 'variants' in args.replay_ignore:
            LOG_UI.warn("Ignoring variants from source job with "
                        "--replay-ignore.")
        else:
            variants = jobdata.retrieve_variants(resultsdir)
            if variants is None:
                LOG_UI.error('Source job variants data not found. Aborting.')
                sys.exit(exit_codes.AVOCADO_FAIL)
            else:
                LOG_UI.warning("Using src job Mux data only, use "
                               "`--replay-ignore variants` to override "
                               "them.")
                setattr(args, "avocado_variants", variants)

        # Extend "replay_test_status" of "INTERRUPTED" when --replay-resume
        # supplied.
        if args.replay_resume:
            if not args.replay_teststatus:
                args.replay_teststatus = ["INTERRUPTED"]
            elif "INTERRUPTED" not in args.replay_teststatus:
                args.replay_teststatus.append("INTERRUPTED")
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
                LOG_UI.warn("Directory used in the replay source job '%s' does"
                            " not exist, using '.' instead", pwd)
