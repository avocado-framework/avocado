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
import logging
import os

from avocado.core.parser import FileOrStdoutAction
from avocado.core.plugin_interfaces import CLI, Result


UNKNOWN = '<unknown>'


class JSONResult(Result):

    name = 'json'
    description = 'JSON result support'

    def _render(self, result):
        tests = []
        for test in result.tests:
            tests.append({'test': str(test.get('name', UNKNOWN)),
                          'url': str(test.get('name', UNKNOWN)),
                          'start': test.get('time_start', -1),
                          'end': test.get('time_end', -1),
                          'time': test.get('time_elapsed', -1),
                          'status': test.get('status', {}),
                          'whiteboard': test.get('whiteboard', UNKNOWN),
                          'logdir': test.get('logdir', UNKNOWN),
                          'logfile': test.get('logfile', UNKNOWN),
                          'fail_reason': str(test.get('fail_reason', UNKNOWN))})
        content = {'job_id': result.job_unique_id,
                   'debuglog': result.logfile,
                   'tests': tests,
                   'total': result.tests_total,
                   'pass': result.passed,
                   'errors': result.errors,
                   'failures': result.failed,
                   'skip': result.skipped,
                   'time': result.tests_total_time}
        return json.dumps(content,
                          sort_keys=True,
                          indent=4,
                          separators=(',', ': '))

    def render(self, result, job):
        if not (hasattr(job.args, 'json_job_result') or
                hasattr(job.args, 'json_output')):
            return

        content = self._render(result)
        if getattr(job.args, 'json_job_result', 'off') == 'on':
            json_path = os.path.join(job.logdir, 'results.json')
            with open(json_path, 'w') as json_file:
                json_file.write(content)

        json_path = getattr(job.args, 'json_output', 'None')
        if json_path is not None:
            if json_path == '-':
                log = logging.getLogger("avocado.app")
                log.debug(content)
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

        run_subcommand_parser.output.add_argument(
            '--json', type=str, action=FileOrStdoutAction,
            dest='json_output', metavar='FILE',
            help='Enable JSON result format and write it to FILE. '
                 "Use '-' to redirect to the standard output.")

        run_subcommand_parser.output.add_argument(
            '--json-job-result', dest='json_job_result',
            choices=('on', 'off'), default='on',
            help=('Enables default JSON result in the job results directory. '
                  'File will be named "results.json".'))

    def run(self, args):
        pass
