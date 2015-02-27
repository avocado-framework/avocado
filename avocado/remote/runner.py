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
# Copyright: Red Hat Inc. 2014-2015
# Author: Ruda Moura <rmoura@redhat.com>

"""Remote test runner."""

import json
import os

from avocado.core import status
from avocado.core import exceptions
from avocado.utils import archive
from avocado.runner import TestRunner
from avocado.remote.test import RemoteTest


class RemoteTestRunner(TestRunner):

    """ Tooled TestRunner to run on remote machine using ssh """
    remote_test_dir = '~/avocado/tests'

    def run_test(self, urls):
        """
        Run tests.

        :param urls: a string with test URLs.
        :return: a dictionary with test results.
        """
        avocado_cmd = ('cd %s; avocado run --force-job-id %s --json - '
                       '--archive %s' % (self.remote_test_dir,
                                         self.result.stream.job_unique_id,
                                         " ".join(urls)))
        result = self.result.remote.run(avocado_cmd, ignore_status=True,
                                        timeout=None)
        if result.exit_status == 127:
            raise exceptions.JobError('Remote machine does not have avocado '
                                      'installed')
        json_result = None
        for json_output in result.stdout.splitlines():
            # We expect dictionary:
            if json_output.startswith('{') and json_output.endswith('}'):
                try:
                    json_result = json.loads(json_output)
                except ValueError:
                    pass

        if json_result is None:
            raise ValueError("Could not parse JSON from avocado remote output:"
                             "\n%s" % result.stdout)

        for t_dict in json_result['tests']:
            logdir = os.path.dirname(self.result.stream.debuglog)
            logdir = os.path.join(logdir, 'test-results')
            logdir = os.path.join(logdir, os.path.relpath(t_dict['url'], '/'))
            t_dict['logdir'] = logdir
            t_dict['logfile'] = os.path.join(logdir, 'debug.log')

        return json_result

    def run_suite(self, test_suite):
        """
        Run one or more tests and report with test result.

        :param params_list: a list of param dicts.

        :return: a list of test failures.
        """
        del test_suite     # using self.result.urls instead
        failures = []
        self.result.setup()
        results = self.run_test(self.result.urls)
        remote_log_dir = os.path.dirname(results['debuglog'])
        self.result.start_tests()
        for tst in results['tests']:
            test = RemoteTest(name=tst['test'],
                              time=tst['time'],
                              start=tst['start'],
                              end=tst['end'],
                              status=tst['status'],
                              logdir=tst['logdir'],
                              logfile=tst['logfile'],
                              fail_reason=tst['fail_reason'])
            state = test.get_state()
            self.result.start_test(state)
            self.result.check_test(state)
            if not status.mapping[state['status']]:
                failures.append(state['tagged_name'])
        local_log_dir = os.path.dirname(self.result.stream.debuglog)
        zip_filename = remote_log_dir + '.zip'
        zip_path_filename = os.path.join(local_log_dir,
                                         os.path.basename(zip_filename))
        self.result.remote.receive_files(local_log_dir, zip_filename)
        archive.uncompress(zip_path_filename, local_log_dir)
        os.remove(zip_path_filename)
        self.result.end_tests()
        self.result.tear_down()
        return failures
