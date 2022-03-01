#!/usr/bin/env python3

"""
Script supposed to be given paths to "results.json" files with same set
of tests.  It points out which tests have *not* passed in the complete
set of jobs.  Useful for running say a 100 jobs, to validate the
stability of jobs/tests and the lack of intermittent failures, race
conditions, etc.
"""

import collections
import json
import sys


def get_one_job_results(path, results):
    with open(path, encoding='utf-8') as result_json:
        js = json.load(result_json)

    job = {}
    for test in js['tests']:
        test_id = test['id']
        if results:
            # we have already parsed at least one job, so that will be
            # used as the baseline for the set of tests that should be
            # present on every job
            if test_id not in results:
                print(f'Test ID "{test_id}" is not present in a previous job, aborting')
                sys.exit(1)
        status = test['status']
        job[test_id] = status
    return job


def merge_results(results, result_json_paths):
    for result_json_path in result_json_paths:
        job = get_one_job_results(result_json_path, results)
        for test_id_key, test_id_value in job.items():
            if test_id_key not in results:
                results[test_id_key] = {}
            status = test_id_value
            if status not in results[test_id_key]:
                results[test_id_key][status] = 0
            results[test_id_key][status] += 1


def main():
    all_job_results = collections.OrderedDict()
    merge_results(all_job_results, sys.argv[1:])
    number_of_jobs = len(sys.argv[1:])
    any_failure = False
    for test in all_job_results:
        if all_job_results[test].get('PASS') != number_of_jobs:
            any_failure = True
            print(test)
            for status, count in all_job_results[test].items():
                print(f"  - {status}: {count}")
    print('Jobs analyzed:', number_of_jobs, '(all PASSed)' if not any_failure else '')


if __name__ == '__main__':
    main()
