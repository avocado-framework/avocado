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
# Copyright: Red Hat Inc. 2014
# Authors: Ruda Moura <rmoura@redhat.com>
#          Cleber Rosa <crosa@redhat.com>

"""
JSON output module.
"""

import json
import os

from avocado.core.future.settings import settings
from avocado.core.output import LOG_UI
from avocado.core.parser import FileOrStdoutAction
from avocado.core.plugin_interfaces import CLI, Result
from avocado.utils import astring


UNKNOWN = '<unknown>'


class JSONResult(Result):

    name = 'json'
    description = 'JSON result support'

    def _render(self, result):
        tests = []
        for test in result.tests:
            fail_reason = test.get('fail_reason', UNKNOWN)
            if fail_reason is not None:
                fail_reason = astring.to_text(fail_reason)
            tests.append({'id': str(test.get('name', UNKNOWN)),
                          'start': test.get('time_start', -1),
                          'end': test.get('time_end', -1),
                          'time': test.get('time_elapsed', -1),
                          'status': test.get('status', {}),
                          'whiteboard': test.get('whiteboard', UNKNOWN),
                          'logdir': test.get('logdir', UNKNOWN),
                          'logfile': test.get('logfile', UNKNOWN),
                          'fail_reason': fail_reason})
        content = {'job_id': result.job_unique_id,
                   'debuglog': result.logfile,
                   'tests': tests,
                   'total': result.tests_total,
                   'pass': result.passed,
                   'errors': result.errors,
                   'failures': result.failed,
                   'skip': result.skipped,
                   'cancel': result.cancelled,
                   'warn': result.warned,
                   'interrupt': result.interrupted,
                   'time': result.tests_total_time}
        return json.dumps(content,
                          sort_keys=True,
                          indent=4,
                          separators=(',', ': '))

    def render(self, result, job):
        json_output = job.config.get('run.json.output')
        json_job_result = job.config.get('run.json.job_result')
        if not (json_job_result or json_output):
            return

        if not result.tests_total:
            return

        content = self._render(result)
        if json_job_result == 'on':
            json_path = os.path.join(job.logdir, 'results.json')
            with open(json_path, 'w') as json_file:
                json_file.write(content)

        json_path = json_output
        if json_path is not None:
            if json_path == '-':
                LOG_UI.debug(content)
            else:
                with open(json_path, 'w') as json_file:
                    json_file.write(content)


class JSONCLI(CLI):

    """
    JSON output
    """

    name = 'json'
    description = "JSON output options for 'run' command"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        help_msg = ('Enable JSON result format and write it to FILE. '
                    'Use "-" to redirect to the standard output.')
        settings.register_option(section='run.json',
                                 key='output',
                                 default=None,
                                 action=FileOrStdoutAction,
                                 help_msg=help_msg,
                                 metavar='FILE',
                                 parser=run_subcommand_parser,
                                 long_arg='--json')

        help_msg = ('Enables default JSON result in the job results '
                    'directory. File will be named "results.json".')
        settings.register_option(section='run.json',
                                 key='job_result',
                                 default='on',
                                 choices=('on', 'off'),
                                 help_msg=help_msg,
                                 parser=run_subcommand_parser,
                                 long_arg='--json-job-result')

    def run(self, config):
        pass
