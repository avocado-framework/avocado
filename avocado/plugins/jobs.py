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
# Copyright: Red Hat Inc. 2020
# Authors: Beraldo Leal <bleal@redhat.com>

"""
Jobs subcommand
"""
import json
import os

from datetime import datetime
from glob import glob

from avocado.core import exit_codes
from avocado.core.output import LOG_UI
from avocado.core.data_dir import get_job_results_dir, get_logs_dir
from avocado.core.future.settings import settings
from avocado.core.plugin_interfaces import CLICmd


class Jobs(CLICmd):
    """
    Implements the avocado 'jobs' subcommand
    """
    name = 'jobs'
    description = 'Manage Avocado jobs'

    def _get_data_from_file(self, filename):
        if not filename or not os.path.isfile(filename):
            raise FileNotFoundError('File not found {}'.format(filename))

        with open(filename, 'r') as fp:
            return json.load(fp)

    def _print_job_details(self, details):
        for key, value in details.items():
            LOG_UI.info("%-15s: %s", key, value)

    def _print_job_tests(self, tests):
        LOG_UI.info("\nTests:\n")
        date_fmt = "%Y/%m/%d %H:%M:%S"
        LOG_UI.info(" Status  End Time              Run Time   Test ID")
        for test in tests:
            end = datetime.fromtimestamp(test.get('end'))
            status = test.get('status')
            method = LOG_UI.info
            if status in ['ERROR', 'FAIL']:
                method = LOG_UI.error
            method(" %-7s %-20s  %.5f    %s",
                   status,
                   end.strftime(date_fmt),
                   float(test.get('time')),
                   test.get('id'))

    def configure(self, parser):
        """
        Add the subparser for the assets action.

        :param parser: The Avocado command line application parser
        :type parser: :class:`avocado.core.parser.ArgumentParser`
        """
        parser = super(Jobs, self).configure(parser)

        subcommands = parser.add_subparsers(dest='jobs_subcommand',
                                            metavar='sub-command')
        subcommands.required = True

        help_msg = 'List all known jobs by Avocado'
        subcommands.add_parser('list', help=help_msg)

        help_msg = ('Show details about a specific job. When passing a Job '
                    'ID, you can use any Job Reference (job_id, "latest", '
                    'or job results path).')
        show_parser = subcommands.add_parser('show', help=help_msg)
        settings.register_option(section='jobs.show',
                                 key='job_id',
                                 help_msg='JOB id',
                                 metavar='JOBID',
                                 default='latest',
                                 nargs='?',
                                 positional_arg=True,
                                 parser=show_parser)

    def handle_list_command(self, jobs_results):
        """Called when 'avocado jobs list' command is executed."""

        for filename in jobs_results.values():
            with open(filename, 'r') as fp:
                job = json.load(fp)
                try:
                    started_ts = job['tests'][0]['start']
                    started = datetime.fromtimestamp(started_ts)
                except IndexError:
                    continue
                LOG_UI.info("%-40s %-26s %3s (%s/%s/%s/%s)",
                            job['job_id'],
                            str(started),
                            job['total'],
                            job['pass'],
                            job['skip'],
                            job['errors'],
                            job['failures'])

        return exit_codes.AVOCADO_ALL_OK

    def handle_show_command(self, config):
        """Called when 'avocado jobs show' command is executed."""

        job_id = config.get('jobs.show.job_id')
        results_dir = get_job_results_dir(job_id)
        if results_dir is None:
            LOG_UI.error("Error: Job %s not found", job_id)
            return exit_codes.AVOCADO_GENERIC_CRASH

        results_file = os.path.join(results_dir, 'results.json')
        config_file = os.path.join(results_dir, 'jobdata/args.json')
        try:
            results_data = self._get_data_from_file(results_file)
        except FileNotFoundError as ex:
            # Results data are important and should exit if not found
            LOG_UI.error(ex)
            return exit_codes.AVOCADO_GENERIC_CRASH

        try:
            config_data = self._get_data_from_file(config_file)
        except FileNotFoundError:
            pass

        data = {'Job id': job_id,
                'Debug log': results_data.get('debuglog'),
                'Spawner': config_data.get('nrun.spawner', 'unknown'),
                '#total tests': results_data.get('total'),
                '#pass tests': results_data.get('pass'),
                '#skip tests': results_data.get('skip'),
                '#errors tests': results_data.get('errors'),
                '#cancel tests': results_data.get('cancel')}

        # We could improve this soon with more data and colors
        self._print_job_details(data)
        self._print_job_tests(results_data.get('tests'))
        return exit_codes.AVOCADO_ALL_OK

    def run(self, config):
        results = {}

        jobs_dir = get_logs_dir()
        for result in glob(os.path.join(jobs_dir, '*/results.json')):
            with open(result, 'r') as fp:
                job = json.load(fp)
                results[job['job_id']] = result

        subcommand = config.get('jobs_subcommand')
        if subcommand == 'list':
            return self.handle_list_command(results)
        elif subcommand == 'show':
            return self.handle_show_command(config)
        return exit_codes.AVOCADO_ALL_OK
