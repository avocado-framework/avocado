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
# Copyright: Red Hat Inc. 2017
# Authors: Amador Pahim <apahim@redhat.com>

"""
Avocado Plugin to propagate Job results to Resultsdb
"""

import sys
import time
import resultsdb_api

from avocado.core.plugin_interfaces import CLI, Result
from avocado.core import exceptions
from avocado.utils import stacktrace


class ResultsdbResult(Result):

    name = 'resultsdb'
    description = 'Resultsdb result support'

    def render(self, result, job):

        if not getattr(job.args, 'resultsdb_api', False):
            return

        if not result.tests_total:
            return

        rdbapi = resultsdb_api.ResultsDBapi(job.args.resultsdb_api)

        for test in result.tests:
            group = [job.unique_id]
            name = unicode(test['name'])
            status = test['status']
            outcome = self._status_map(status)
            note = None
            if test['fail_reason'] is not None:
                note = str(test['fail_reason'])

            local_time_start = time.localtime(test['time_start'])
            local_time_end = time.localtime(test['time_end'])
            data = {'time_elapsed': "%.2f s" % test['time_elapsed'],
                    'time_start': time.strftime("%Y-%m-%d %H:%M:%S",
                                                local_time_start),
                    'time_end': time.strftime("%Y-%m-%d %H:%M:%S",
                                              local_time_end),
                    'logdir': test['logdir'],
                    'logfile': test['logfile'],
                    'whiteboard': test['whiteboard']}

            rdbapi.create_result(outcome,
                                 name,
                                 group,
                                 note,
                                 **data)

    @staticmethod
    def _status_map(status):
        """
        Returns the resultsdb corresponding status to Avocado status.
        Valid statuses are:
         PASSED
         FAILED
         INFO
         NEEDS_INSPECTION
        """
        mapping = {'PASS': 'PASSED',
                   'FAIL': 'FAILED',
                   'ERROR': 'FAILED',
                   'INTERRUPTED': 'FAILED',
                   'SKIP': 'INFO',
                   'CANCEL': 'INFO',
                   'WARN': 'INFO'}

        if status in mapping:
            return mapping[status]

        return 'NEEDS_INSPECTION'


class ResultsdbCLI(CLI):

    """
    Propagate Job results to Resultsdb
    """

    name = 'resultsdb'
    description = "Resultsdb options for 'run' subcommand"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        msg = 'resultsdb options'
        parser = run_subcommand_parser.add_argument_group(msg)
        parser.add_argument('--resultsdb-api',
                            dest='resultsdb_api', default=None,
                            help='Specify the resultsdb API url')
        self.configured = True

    def run(self, args):
        if not getattr(args, 'resultsdb_api', False):
            return
