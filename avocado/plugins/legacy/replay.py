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

from avocado.core import data_dir, exit_codes, jobdata, teststatus
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

        help_msg = ('Replay a job identified by its (partial) hash id. '
                    'Use "--replay" latest to replay the latest job.')
        settings.register_option(section='run.replay',
                                 key='job_id',
                                 default=None,
                                 help_msg=help_msg,
                                 parser=replay_parser,
                                 long_arg='--replay',
                                 metavar='JOB_ID')

        help_msg = 'Filter tests to replay by test status.'
        settings.register_option(section='run.replay',
                                 key='test_status',
                                 default=[],
                                 help_msg=help_msg,
                                 key_type=self._valid_status,
                                 parser=replay_parser,
                                 long_arg='--replay-test-status',
                                 metavar='TEST_STATUS')

        help_msg = 'Ignore variants and/or configuration from the source job.'
        settings.register_option(section='run.replay',
                                 key='ignore',
                                 default=[],
                                 help_msg=help_msg,
                                 key_type=self._valid_ignore,
                                 parser=replay_parser,
                                 long_arg='--replay-ignore',
                                 metavar='IGNORE')

        help_msg = 'Resume an interrupted job'
        settings.register_option(section='run.replay',
                                 key='resume',
                                 default=False,
                                 help_msg=help_msg,
                                 key_type=bool,
                                 parser=replay_parser,
                                 long_arg='--replay-resume')

    @staticmethod
    def _valid_status(string):
        if not string:
            return []
        status_list = string.split(',')
        for item in status_list:
            if item not in teststatus.STATUSES:
                msg = ('Invalid --replay-test-status option. Valid '
                       'options are (more than one allowed): %s' %
                       ','.join([item for item
                                 in teststatus.STATUSES]))
                raise argparse.ArgumentTypeError(msg)

        return status_list

    @staticmethod
    def _valid_ignore(string):
        if not string:
            return []
        options = ['variants', 'config']
        ignore_list = string.split(',')
        for item in ignore_list:
            if item not in options:
                msg = ('Invalid --replay-ignore option. Valid '
                       'options are (more than one allowed): %s'
                       % ','.join(options))
                raise argparse.ArgumentTypeError(msg)

        return ignore_list

    @staticmethod
    def load_config(resultsdir):
        config = jobdata.retrieve_config(resultsdir)
        if config is not None:
            settings.process_config_path(config)

    @staticmethod
    def _get_tests_from_tap(path):
        if not os.path.exists(path):
            return None
        re_result = re.compile(r"(not )?ok (\d+) ([^#]*)(# (\w+).*)?")
        re_no_tests = re.compile(r"1..(\d+)")
        max_index = 0
        no_tests = 0
        _tests = {}
        with open(path) as tapfile:
            for line in tapfile:
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
                for i in range(1, max(max_index, no_tests) + 1)]

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
                for _ in range(results["total"] - len(tests)):
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

    def run(self, config):
        job_id = config.get('run.replay.job_id')
        if job_id is None:
            return

        err = None
        replay_ignore = config.get('run.replay.ignore')
        test_status = config.get('run.replay.test_status')

        if test_status and 'variants' in replay_ignore:
            err = ("Option `--replay-test-status` is incompatible with "
                   "`--replay-ignore variants`.")
        elif test_status and config.get('run.references'):
            err = ("Option --replay-test-status is incompatible with "
                   "test references given on the command line.")
        elif config.get("remote_hostname", False):
            err = "Currently we don't replay jobs in remote hosts."
        if err is not None:
            LOG_UI.error(err)
            sys.exit(exit_codes.AVOCADO_FAIL)

        resultsdir = data_dir.get_job_results_dir(job_id,
                                                  config.get('run.results_dir'))
        if resultsdir is None:
            LOG_UI.error("Can't find job results directory for '%s'", job_id)
            sys.exit(exit_codes.AVOCADO_FAIL)

        with open(os.path.join(resultsdir, 'id'), 'r') as id_file:
            config['replay_sourcejob'] = id_file.read().strip()

        replay_config = jobdata.retrieve_job_config(resultsdir)
        overridables = ['loaders',
                        'external_runner',
                        'external_runner_testdir',
                        'external_runner_chdir',
                        'failfast',
                        'ignore_missing_references',
                        'execution_order']
        if replay_config is None:
            LOG_UI.warn('Source job config data not found. These options will '
                        'not be loaded in this replay job: %s',
                        ', '.join(overridables))
        else:
            for option in overridables:
                optvalue = config.get(option, None)
                # Temporary, this will be removed soon
                if option in ['failfast',
                              'ignore_missing_references',
                              'execution_order',
                              'loaders',
                              'external_runner',
                              'external_runner_chdir',
                              'external_runner_testdir']:
                    optvalue = config.get('run.{}'.format(option))
                if optvalue is not None:
                    LOG_UI.warn("Overriding the replay %s with the --%s value "
                                "given on the command line.",
                                option.replace('_', '-'),
                                option.replace('_', '-'))
                elif option in replay_config:
                    config[option] = replay_config[option]

        if config.get('run.references'):
            LOG_UI.warn('Overriding the replay test references with test '
                        'references given in the command line.')
        else:
            references = jobdata.retrieve_references(resultsdir)
            if references is None:
                LOG_UI.error('Source job test references data not found. '
                             'Aborting.')
                sys.exit(exit_codes.AVOCADO_FAIL)
            else:
                config['run.references'] = references

        if 'config' in replay_ignore:
            LOG_UI.warn("Ignoring configuration from source job with "
                        "--replay-ignore.")
        else:
            self.load_config(resultsdir)

        if 'variants' in replay_ignore:
            LOG_UI.warn("Ignoring variants from source job with "
                        "--replay-ignore.")
        else:
            variants = jobdata.get_variants_path(resultsdir)
            if variants is None:
                LOG_UI.error('Source job variants data not found. Aborting.')
                sys.exit(exit_codes.AVOCADO_FAIL)
            else:
                LOG_UI.warning("Using src job variants data only, use "
                               "`--replay-ignore variants` to override "
                               "them.")
                config["json.variants.load"] = variants

        # Extend "replay_test_status" of "INTERRUPTED" when --replay-resume
        # supplied.
        if config.get('run.replay.resume'):
            if not test_status:
                config['replay_teststatus'] = ["INTERRUPTED"]
            elif "INTERRUPTED" not in test_status:
                config['replay_teststatus'].append("INTERRUPTED")
        if test_status:
            replay_map = self._create_replay_map(resultsdir,
                                                 test_status)
            config['replay_map'] = replay_map

        # Use the original directory to resolve test references properly
        pwd = jobdata.retrieve_pwd(resultsdir)
        if pwd is not None:
            if os.path.exists(pwd):
                os.chdir(pwd)
            else:
                LOG_UI.warn("Directory used in the replay source job '%s' does"
                            " not exist, using '.' instead", pwd)
