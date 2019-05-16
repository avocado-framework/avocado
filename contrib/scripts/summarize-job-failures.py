#!/usr/bin/env python

"""
Script support to be given paths to "results.json" files with same set
of tests.  It points out which tests have *not* passed in the complete
set of jobs.  Useful for running say a 100 jobs, to validate the
stability of jobs/tests and the lack of intermittent failures, race
conditions, etc.
"""

import collections
import json
import sys

tests = collections.OrderedDict()

for result_json_path in sys.argv[1:]:
    with open(result_json_path) as result_json:
        js = json.load(result_json)

    for test in js['tests']:
        test_id = test['id']
        if test_id not in tests:
            tests[test_id] = {}
        status = test['status']
        if status not in tests[test_id]:
            tests[test_id][status] = 0
        tests[test_id][status] += 1

jobs = len(sys.argv[1:])
print('Jobs analyzed: ', jobs)
for test in tests:
    if tests[test].get('PASS') != jobs:
        print(test)
        for status, count in tests[test].items():
            print("  - %s: %s" % (status, count))
