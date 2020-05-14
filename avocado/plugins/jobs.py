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
from avocado.core.data_dir import get_logs_dir
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd


class Jobs(CLICmd):
    """
    Implements the avocado 'jobs' subcommand
    """
    name = 'jobs'
    description = 'Manage Avocado jobs'

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
        return exit_codes.AVOCADO_ALL_OK
