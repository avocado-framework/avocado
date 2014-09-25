#!/usr/bin/env python

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

import unittest
import os
import sys
import json
import argparse

# simple magic for using scripts within a source tree
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
basedir = os.path.dirname(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.core import status
from avocado.core import job_id
from avocado.plugins import vm


class _Stream(object):
    job_unique_id = job_id.create_unique_job_id()

    def start_file_logging(self, param1, param2):
        pass

    def stop_file_logging(self):
        pass

    def log(self, msg, skip_newline=False):
        pass

    def log_ui_header(self, param):
        pass

    def log_ui_status_pass(self, param1):
        pass


class VMResultTest(unittest.TestCase):

    def setUp(self):
        args = argparse.Namespace()
        stream = _Stream()
        stream.logfile = 'debug.log'
        self.test_result = vm.VMTestResult(stream, args)
        j = '''{"tests": [{"test": "sleeptest.1", "url": "sleeptest", "status": "PASS", "time": 1.23}],
                "debuglog": "/home/user/avocado/logs/run-2014-05-26-15.45.37/debug.log",
                "errors": 0, "skip": 0, "time": 1.4,
                "pass": 1, "failures": 0, "total": 1}'''
        self.results = json.loads(j)

    def test_check(self):
        failures = []
        self.test_result.start_tests()
        for tst in self.results['tests']:
            test = vm.Test(name=tst['test'],
                           time=tst['time'],
                           status=tst['status'])
            self.test_result.start_test(test.get_state())
            self.test_result.check_test(test.get_state())
            if not status.mapping[test.status]:
                failures.append(test.tagged_name)
        self.test_result.end_tests()
        self.assertEqual(self.test_result.tests_total, 1)
        self.assertEqual(len(self.test_result.passed), 1)
        self.assertEqual(len(self.test_result.failed), 0)
        self.assertEqual(len(failures), 0)


if __name__ == '__main__':
    unittest.main()
