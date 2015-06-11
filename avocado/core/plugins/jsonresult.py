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

from . import plugin
from .. import output
from ..result import TestResult


class JSONTestResult(TestResult):

    """
    JSON Test Result class.
    """

    command_line_arg_name = '--json'

    def __init__(self, stream=None, args=None):
        TestResult.__init__(self, stream, args)
        self.output = getattr(self.args, 'json_output', '-')
        self.view = output.View(app_args=args)

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

        :param state: result of :class:`avocado.core.test.Test.get_state`.
        :type state: dict
        """
        TestResult.end_test(self, state)
        if 'job_id' not in self.json:
            self.json['job_id'] = state['job_unique_id']
        t = {'test': state['tagged_name'],
             'url': state['name'],
             'start': state['time_start'],
             'end': state['time_end'],
             'time': state['time_elapsed'],
             'status': state['status'],
             'whiteboard': state['whiteboard'],
             'logdir': state['logdir'],
             'logfile': state['logfile'],
             'fail_reason': str(state['fail_reason'])
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
            self.view.notify(event='minor', msg=self.json)
        else:
            self._save_json()


class JSON(plugin.Plugin):

    """
    JSON output
    """

    name = 'json'
    enabled = True

    def configure(self, parser):
        self.parser = parser
        self.parser.runner.output.add_argument(
            '--json', type=str,
            dest='json_output',
            help='Enable JSON output to the file where the result should be written. '
                 "Use '-' to redirect to the standard output.")
        self.configured = True

    def activate(self, app_args):
        try:
            if app_args.json_output:
                self.parser.application.set_defaults(json_result=JSONTestResult)
        except AttributeError:
            pass
