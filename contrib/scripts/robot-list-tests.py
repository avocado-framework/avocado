#!/usr/bin/python
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: 2017 Red Hat, Inc.
# Author: Amador Pahim <apahim@redhat.com>

#
# This script receives the path of a robot suite and creates a list of
# tests to be used by Avocado to execute with the external-runner
# robot-test-runner.py
#
# Usage: ./robot-list-tests.py <path>
# Example: ./robot-list-tests.py ~/Downloads/WebDemo/login_tests/


import sys

from robot.parsing.model import TestData


def find_tests(data, test_suite={}):
    test_suite[data.name] = []
    for test in data.testcase_table:
        test_suite[data.name].append(test.name)
    for child_data in data.children:
        find_tests(child_data, test_suite)
    return test_suite


for pathname in sys.argv[1:]:
    data = TestData(parent=None, source=pathname)
    test_suite = find_tests(data)
    for ts in test_suite:
        for test in test_suite[ts]:
            print('"\\"%s:%s:%s\\\""' % (pathname, ts, test))
