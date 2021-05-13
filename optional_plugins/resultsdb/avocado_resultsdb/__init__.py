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

import os
import time

import resultsdb_api

from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLI, Result, ResultEvents
from avocado.core.settings import settings


class ResultsdbResultEvent(ResultEvents):

    """
    ResultsDB output class
    """

    name = 'resultsdb'
    description = 'Resultsdb result support'

    def __init__(self, config):
        self.rdbapi = None
        resultsdb_api_url = config.get('plugins.resultsdb.api_url')
        if resultsdb_api_url is not None:
            self.rdbapi = resultsdb_api.ResultsDBapi(resultsdb_api_url)

        self.rdblogs = config.get('plugins.resultsdb.logs_url')
        self.rdbnote_limit = config.get('plugins.resultsdb.note_size_limit')
        self.job_id = None
        self.job_logdir = None

    def pre_tests(self, job):
        """
        Create the ResultsDB group, which corresponds to the Avocado Job
        """
        if self.rdbapi is None:
            return

        self.job_id = job.unique_id
        self.job_logdir = os.path.basename(job.logdir)

        ref_url = None
        if self.rdblogs is not None:
            ref_url = '%s/%s' % (self.rdblogs, self.job_logdir)

        self.rdbapi.create_group(self.job_id, ref_url, self.job_logdir)

    def start_test(self, result, state):
        pass

    def end_test(self, result, state):
        """
        Create the ResultsDB result, which corresponds to one test from
        the Avocado Job
        """
        if self.rdbapi is None:
            return

        outcome = self._status_map(state['status'])
        name = state['name'].name
        if state['name'].variant is not None:
            name += ';%s' % state['name'].variant
        group = [self.job_id]

        note = None
        if state['fail_reason'] is not None:
            note = str(state['fail_reason'])
            if self.rdbnote_limit > 0 and len(note) > self.rdbnote_limit:
                note = note[0:self.rdbnote_limit] + '...'

        ref_url = None
        if self.rdblogs is not None:
            logdir = os.path.basename(state['logdir'])
            ref_url = '%s/%s/test-results/%s' % (self.rdblogs,
                                                 self.job_logdir,
                                                 logdir)

        local_time_start = time.localtime(state['time_start'])
        local_time_end = time.localtime(state['time_end'])
        data = {'time_elapsed': "%.2f s" % state['time_elapsed'],
                'time_start': time.strftime("%Y-%m-%d %H:%M:%S",
                                            local_time_start),
                'time_end': time.strftime("%Y-%m-%d %H:%M:%S",
                                          local_time_end),
                'logdir': state['logdir'],
                'logfile': state['logfile'],
                'whiteboard': state['whiteboard'],
                'status': state['status']}

        params = {}
        if state['params']:
            for path, key, value in state['params']:
                params['param %s' % key] = '%s (path: %s)' % (value, path)
            data.update(params)

        self.rdbapi.create_result(outcome, name, group, note, ref_url, **data)

    def test_progress(self, progress=False):
        pass

    def post_tests(self, job):
        pass

    @staticmethod
    def _status_map(status):
        """
        Returns the resultsdb corresponding status to the Avocado status
        Valid ResultsDB statuses in v2.0 are:
         - PASSED
         - FAILED
         - INFO (treat as PASSED and flag for human review)
         - NEEDS_INSPECTION (treat as FAILED and flag for human review)
        """
        mapping = {'PASS': 'PASSED',
                   'FAIL': 'FAILED',
                   'SKIP': 'INFO',
                   'CANCEL': 'INFO',
                   'INTERRUPTED': 'INFO',
                   'WARN': 'INFO'}

        if status in mapping:
            return mapping[status]

        return 'NEEDS_INSPECTION'


class ResultsdbResult(Result):

    """
    ResultsDB render class
    """

    name = 'resultsdb'
    description = 'Resultsdb result support'

    def render(self, result, job):
        resultsdb_logs = job.config.get('plugins.resultsdb.logs_url')
        stdout_claimed_by = job.config.get('stdout_claimed_by')
        if (resultsdb_logs is not None and stdout_claimed_by is None):
            log_msg = "JOB URL    : %s/%s"
            LOG_UI.info(log_msg,
                        resultsdb_logs,
                        os.path.basename(job.logdir))


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
        help_msg = 'Specify the resultsdb API url'
        settings.register_option(section='plugins.resultsdb',
                                 key='api_url',
                                 default=None,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--resultsdb-api',
                                 metavar='API_URL')

        help_msg = 'Specify the URL where the logs are published'
        settings.register_option(section='plugins.resultsdb',
                                 key='logs_url',
                                 default=None,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--resultsdb-logs',
                                 metavar='LOGS_URL')

        help_msg = 'Maximum note size limit'
        settings.register_option(section='plugins.resultsdb',
                                 key='note_size_limit',
                                 default=0,
                                 key_type=int,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--resultsdb-note-limit',
                                 metavar='SIZE_LIMIT')

    def run(self, config):
        pass
