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
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Class that describes a sequence of automated operations.
"""
import imp
import logging
import os
import time
import uuid

from avocado.core import data_dir
from avocado.core import output
from avocado.core import status
from avocado import test
from avocado import result


class Job(object):

    """
    A Job is a set of operations performed on a test machine.

    Most of the time, we are interested in simply running tests,
    along with setup operations and event recording.
    """

    def __init__(self, args=None):
        self.args = args
        self.unique_id = args.unique_id or str(uuid.uuid4())
        start_time = time.strftime('%Y-%m-%d-%H.%M.%S')
        if self.args is not None:
            logdir = args.logdir or data_dir.get_logs_dir()
        else:
            logdir = data_dir.get_logs_dir()
        debugbase = 'run-%s' % start_time
        self.debugdir = os.path.join(logdir, debugbase)
        if not os.path.isdir(self.debugdir):
            os.makedirs(self.debugdir)
        latestdir = os.path.join(logdir, "latest")
        try:
            os.unlink(latestdir)
        except OSError:
            pass
        os.symlink(debugbase, latestdir)

        self.debuglog = os.path.join(self.debugdir, "debug.log")
        if self.args is not None:
            self.loglevel = args.log_level or logging.DEBUG
        else:
            self.loglevel = logging.DEBUG
        self.test_dir = data_dir.get_test_dir()
        self.test_index = 1
        self.status = "RUNNING"

        self.output_manager = output.OutputManager()

    def _load_test_instance(self, url):
        path_attempt = os.path.abspath(url)
        if os.path.exists(path_attempt):
            test_class = test.DropinTest
            test_instance = test_class(path=path_attempt,
                                       base_logdir=self.debugdir,
                                       job=self)
        else:
            test_module_dir = os.path.join(self.test_dir, url)
            f, p, d = imp.find_module(url, [test_module_dir])
            test_module = imp.load_module(url, f, p, d)
            f.close()
            test_class = getattr(test_module, url)
            test_instance = test_class(name=url,
                                       base_logdir=self.debugdir,
                                       job=self)
        return test_instance

    def run_test(self, url):
        """
        Run a single test URL.
        """
        test_instance = self._load_test_instance(url)
        test_instance.run_avocado()
        return test_instance

    def _make_test_result(self, urls):
        if hasattr(self.args, 'test_result'):
            test_result_class = self.args.test_result
        else:
            test_result_class = result.HumanTestResult
        test_result = test_result_class(self.output_manager,
                                        self.debuglog,
                                        self.loglevel,
                                        len(urls),
                                        self.args)
        return test_result

    def run(self, urls=None):
        """
        Main job method. Runs a list of test URLs to its completion.

        :param urls: String with tests to run.

        :return: Integer with overall job status
                 0 - Job passed, all tests passed
                 1 - Job passed, some/all tests failed
                 2 - Job failed
        """
        failures = []
        if urls is None:
            urls = self.args.url.split()

        test_result = self._make_test_result(urls)

        test_result.start_tests()
        for url in urls:
            test_instance = self.run_test(url)
            test_result.check_test(test_instance)
            if not status.mapping[test_instance.status]:
                failures.append(test_instance.name)
        test_result.end_tests()
        # If it's all good so far, set job status to 'PASS'
        if self.status == 'RUNNING':
            self.status = 'PASS'
        # Let's assess the overall status:
        job_status = status.mapping[self.status]
        tests_status = not bool(failures)
        if job_status:
            if tests_status:
                return 0
            else:
                return 1
        else:
            return 2


class TestModuleRunner(object):

    """
    Convenience class to make avocado test modules executable.
    """

    def __init__(self, module='__main__'):
        if isinstance(module, basestring):
            self.module = __import__(module)
            for part in module.split('.')[1:]:
                self.module = getattr(self.module, part)
        else:
            self.module = module
        url = None
        for key, value in self.module.__dict__.iteritems():
            try:
                if issubclass(value, test.Test):
                    url = key
            except TypeError:
                pass
        self.job = Job()
        if url is not None:
            self.job.run(urls=[url])

main = TestModuleRunner
