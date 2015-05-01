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
import re

from avocado.core import exceptions
from avocado.core import status
from avocado.core.remote.test import RemoteTest
from avocado.runner import TestRunner
from avocado.utils import archive
from fabric.exceptions import CommandTimeout


class RemoteTestRunner(TestRunner):

    """ Tooled TestRunner to run on remote machine using ssh """
    remote_test_dir = '~/avocado/tests'

    remote_version_re = re.compile(r'^Avocado (\d+)\.(\d+)\.(\d+)$')

    def check_remote_avocado(self):
        """
        Checks if the remote system appears to have avocado installed

        The "appears to have" description is justified by the fact that the
        check is rather simplistic, it attempts to run an `avocado -v` command
        and checks if the output looks like what avocado would print out.

        :rtype: tuple with (bool, tuple)
        :returns: (True, (x, y, z)) if avocado appears to be installed and
                  (False, None) otherwise.
        """
        result = self.result.remote.run('avocado -v',
                                        ignore_status=True,
                                        timeout=60)
        if result.exit_status == 127:
            return (False, None)

        match = self.remote_version_re.match(result.stdout)
        if match is None:
            return (False, None)

        return (True, tuple(map(int, match.groups())))

    def run_test(self, urls, timeout):
        """
        Run tests.

        :param urls: a string with test URLs.
        :return: a dictionary with test results.
        """
        avocado_installed_version = self.check_remote_avocado()
        if not avocado_installed_version[0]:
            raise exceptions.JobError('Remote machine does not seem to have '
                                      'avocado installed')

        urls_str = " ".join(urls)
        avocado_check_urls_cmd = ('cd %s; avocado list %s '
                                  '--paginator=off' % (self.remote_test_dir,
                                                       urls_str))
        check_urls_result = self.result.remote.run(avocado_check_urls_cmd,
                                                   ignore_status=True,
                                                   timeout=60)
        if check_urls_result.exit_status != 0:
            raise exceptions.JobError(check_urls_result.stdout)

        avocado_cmd = ('cd %s; avocado run --force-job-id %s --json - '
                       '--archive %s' % (self.remote_test_dir,
                                         self.result.stream.job_unique_id,
                                         urls_str))
        try:
            result = self.result.remote.run(avocado_cmd, ignore_status=True,
                                            timeout=timeout)
        except CommandTimeout:
            raise exceptions.JobError("Remote execution took longer than "
                                      "specified timeout (%s). Interrupting."
                                      % (timeout))
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
            relative_path = t_dict['url'].lstrip('/')
            logdir = os.path.join(logdir, relative_path)
            t_dict['logdir'] = logdir
            t_dict['logfile'] = os.path.join(logdir, 'debug.log')

        return json_result

    def run_suite(self, test_suite, mux, timeout):
        """
        Run one or more tests and report with test result.

        :param params_list: a list of param dicts.
        :param mux: A multiplex iterator (unused here)

        :return: a list of test failures.
        """
        del test_suite     # using self.result.urls instead
        del mux            # we're not using multiplexation here
        if not timeout:     # avoid timeout = 0
            timeout = None
        failures = []
        self.result.setup()
        results = self.run_test(self.result.urls, timeout)
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
