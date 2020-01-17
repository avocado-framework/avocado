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
# Copyright: Red Hat Inc. 2019-2020
# Authors: Cleber Rosa <crosa@redhat.com>

"""
NRunner based implementation of job compliant runner
"""

from avocado.core import test
from avocado.core.plugin_interfaces import Runner as RunnerInterface

from .nrun import check_tasks_requirements


class Runner(RunnerInterface):

    name = 'nrunner'
    description = '*EXPERIMENTAL* nrunner based implementation of job compliant runner'

    #: registry of known test runners
    KNOWN_EXTERNAL_RUNNERS = {}

    def run_suite(self, job, result, test_suite, variants, timeout=0,
                  replay_map=None, execution_order=None):
        summary = set()
        test_suite = check_tasks_requirements(
            test_suite,
            self.KNOWN_EXTERNAL_RUNNERS)  # pylint: disable=W0201
        result.tests_total = len(test_suite)  # no support for variants yet
        result_dispatcher = job.result_events_dispatcher

        for index, task in enumerate(test_suite):
            index += 1
            # this is all rubbish data
            early_state = {
                'name': test.TestID(index, task.identifier),
                'job_logdir': job.logdir,
                'job_unique_id': job.unique_id,
            }
            result.start_test(early_state)
            job.result_events_dispatcher.map_method('start_test',
                                                    result,
                                                    early_state)

            statuses = []
            task.status_services = []
            for status in task.run():
                result_dispatcher.map_method('test_progress', False)
                statuses.append(status)
                if status['status'] not in ["init", "running"]:
                    break

            # test execution time is currently missing
            test_state = {'status': statuses[-1]['status'].upper()}
            test_state.update(early_state)

            time_start = statuses[0]['time_start']
            time_end = statuses[-1]['time_end']
            time_elapsed = time_end - time_start
            test_state['time_start'] = time_start
            test_state['time_end'] = time_end
            test_state['time_elapsed'] = time_elapsed

            # fake log dir, needed by some result plugins such as HTML
            test_state['logdir'] = ''

            result.check_test(test_state)
            result_dispatcher.map_method('end_test', result, test_state)
        return summary
