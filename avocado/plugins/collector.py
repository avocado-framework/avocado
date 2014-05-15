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
# Copyright: Red Hat Inc. 2013-2014
# Author: Ruda Moura <rmoura@redhat.com>

"""
Collect test results for further usage.
"""

import json

from avocado.plugins import plugin
from avocado.result import TestResult


class CollectorTestResult(TestResult):

    """
    Collector TestResult class.
    """

    def __init__(self, stream=None, debuglog=None, loglevel=None,
                 urls=[], args=None):
        TestResult.__init__(self, stream, debuglog, loglevel, urls, args)
        self.json = {'debuglog': debuglog,
                     'tests': []}

    def start_tests(self):
        TestResult.start_tests(self)
        self.stream.start_file_logging(self.debuglog, self.loglevel)

    def end_test(self, test):
        TestResult.end_test(self, test)
        self.stream.stop_file_logging()
        # TODO: real Test class serialization
        t = {'test': test.tagged_name,
             'url': test.name,
             'time': test.time_elapsed,
             'status': test.status,
             }
        self.json['tests'].append(t)
        self.json.update({
            'total': self.tests_total,
            'pass': len(self.passed),
            'errors': len(self.errors),
            'failures': len(self.failed),
            'skip': len(self.skipped),
            'time': self.total_time
        })

    def end_tests(self):
        TestResult.end_tests(self)
        print json.dumps(self.json)


class Collector(plugin.Plugin):

    """
    Collector plugin class.
    """

    name = 'collector'
    enabled = True

    def configure(self, app_parser, cmd_parser):
        self.parser = app_parser
        app_parser.add_argument('--collect', action='store_true')
        self.configured = True

    def activate(self, app_args):
        if app_args.collect:
            self.parser.set_defaults(test_result=CollectorTestResult)
