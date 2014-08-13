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

from avocado.plugins import plugin
from avocado.result import TestResult


class JSONTestResult(TestResult):

    """
    JSON Test Result class.
    """

    def set_output(self):
        self.output = getattr(self.args, 'json_output', '-')

    def set_output_option(self):
        self.output_option = '--json'

    def start_tests(self):
        """
        Called once before any tests are executed.
        """
        TestResult.start_tests(self)
        self.json = {'debuglog': self.stream.logfile,
                     'tests': []}

    def end_test(self, state):
        """
        Called when the given test has been run.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        TestResult.end_test(self, state)
        if 'job_id' not in self.json:
            self.json['job_id'] = state['job_unique_id']
        t = {'test': state['tagged_name'],
             'url': state['name'],
             'time': state['time_elapsed'],
             'status': state['status'],
             'whiteboard': state['whiteboard'],
             }
        self.json['tests'].append(t)

    def _save_json(self):
        with open(self.args.json_output, 'w') as j:
            j.write(self.json)

    def end_tests(self):
        """
        Called once after all tests are executed.
        """
        TestResult.end_tests(self)
        self.json.update({
            'total': self.tests_total,
            'pass': len(self.passed),
            'errors': len(self.errors),
            'failures': len(self.failed),
            'skip': len(self.skipped),
            'time': self.total_time
        })
        self.json = json.dumps(self.json)
        if self.args.json_output == '-':
            print self.json
        else:
            self._save_json()


class JSON(plugin.Plugin):

    """
    JSON output
    """

    name = 'json'
    enabled = True

    def configure(self, app_parser, cmd_parser):
        self.parser = app_parser
        self.parser.add_argument('--json', action='store_true', default=False)
        self.parser.add_argument('--json-output', default='-', type=str,
                                 dest='json_output',
                                 help='the file where the result should be written')
        self.configured = True

    def activate(self, app_args):
        if app_args.json:
            self.parser.set_defaults(json_result=JSONTestResult)
