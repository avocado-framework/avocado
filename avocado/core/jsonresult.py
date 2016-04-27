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
# Author: Ruda Moura <rmoura@redhat.com>

"""
JSON output module.
"""

import json
import logging

from .result import TestResult


class JSONTestResult(TestResult):

    """
    JSON Test Result class.
    """

    command_line_arg_name = '--json'

    def __init__(self, job, force_json_file=None):
        """
        :param job: Job which defines this result
        :param force_json_file: Override the json output file location
        """
        TestResult.__init__(self, job)
        if force_json_file:
            self.output = force_json_file
        else:
            self.output = getattr(self.args, 'json_output', '-')
        self.json = None
        self.log = logging.getLogger("avocado.app")

    def start_tests(self):
        """
        Called once before any tests are executed.
        """
        TestResult.start_tests(self)
        self.json = {'debuglog': self.logfile,
                     'tests': []}

    def end_test(self, state):
        """
        Called when the given test has been run.

        :param state: result of :class:`avocado.core.test.Test.get_state`.
        :type state: dict
        """
        TestResult.end_test(self, state)
        if 'job_id' not in self.json:
            self.json['job_id'] = state.get('job_unique_id', "<unknown>")
        t = {'test': str(state.get('name', "<unknown>")),
             'url': str(state.get('name', "<unknown>")),
             'start': state.get('time_start', -1),
             'end': state.get('time_end', -1),
             'time': state.get('time_elapsed', -1),
             'status': state.get('status', {}),
             'whiteboard': state.get('whiteboard', "<unknown>"),
             'logdir': state.get('logdir', "<unknown>"),
             'logfile': state.get('logfile', "<unknown>"),
             'fail_reason': str(state.get('fail_reason', "<unknown>"))
             }
        self.json['tests'].append(t)

    def _save_json(self):
        with open(self.output, 'w') as j:
            j.write(self.json)

    def end_tests(self):
        """
        Called once after all tests are executed.
        """
        TestResult.end_tests(self)
        self.json.update({
            'total': self.tests_total,
            'pass': self.passed,
            'errors': self.errors,
            'failures': self.failed,
            'skip': self.skipped,
            'time': self.total_time
        })
        self.json = json.dumps(self.json)
        if self.output == '-':
            self.log.debug(self.json)
        else:
            self._save_json()
