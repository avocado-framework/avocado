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
# Authors: Lucas Meneghel Rodrigues <lmr@redhat.com>
#          Ruda Moura <rmoura@redhat.com>

"""
Test loader module.
"""

import os
import imp
import inspect

from avocado import test
from avocado.core import data_dir
from avocado.utils import path


class TestLoader(object):

    """
    Test loader class.
    """

    def __init__(self, job):
        self.job = job

    def _make_missing_test(self, test_name, params):
        test_class = test.MissingTest
        test_parameters = {'name': test_name,
                           'base_logdir': self.job.logdir,
                           'params': params,
                           'job': self.job}
        return test_class, test_parameters

    def _make_not_a_test(self, test_name, params):
        test_class = test.NotATest
        test_parameters = {'name': test_name,
                           'base_logdir': self.job.logdir,
                           'params': params,
                           'job': self.job}
        return test_class, test_parameters

    def _make_simple_test(self, test_path, params):
        test_class = test.SimpleTest
        test_parameters = {'path': test_path,
                           'base_logdir': self.job.logdir,
                           'params': params,
                           'job': self.job}
        return test_class, test_parameters

    def _make_test(self, test_name, test_path, params, queue):
        module_name = os.path.basename(test_path).split('.')[0]
        test_module_dir = os.path.dirname(test_path)
        test_class = None
        test_parameters_simple = {'path': test_path,
                                  'base_logdir': self.job.logdir,
                                  'params': params,
                                  'job': self.job}

        test_parameters_queue = {'name': test_name,
                                 'base_logdir': self.job.logdir,
                                 'params': params,
                                 'job': self.job,
                                 'runner_queue': queue}
        try:
            f, p, d = imp.find_module(module_name, [test_module_dir])
            test_module = imp.load_module(module_name, f, p, d)
            f.close()
            for name, obj in inspect.getmembers(test_module):
                if inspect.isclass(obj):
                    if issubclass(obj, test.Test):
                        test_class = obj
            if test_class is not None:
                # Module is importable and does have an avocado test class inside, let's proceed.
                test_parameters = test_parameters_queue
            else:
                if os.access(test_path, os.X_OK):
                    # Module does not have an avocado test class inside but it's executable, let's execute it.
                    test_class = test.SimpleTest
                    test_parameters = test_parameters_simple
                else:
                    # Module does not have an avocado test class inside, and it's not executable. Not a Test.
                    test_class = test.NotATest
                    test_parameters = test_parameters_queue

        except ImportError, details:
            if os.access(test_path, os.X_OK):
                # Module can't be imported, and it's executable. Let's try to execute it.
                test_class = test.SimpleTest
                test_parameters = test_parameters_simple
            else:
                # Module can't be imported and it's not an executable. Our best guess is that this is a buggy test.
                test_class = test.BuggyTest
                params['exception'] = details
                test_parameters = test_parameters_queue

        return test_class, test_parameters

    def discover_test(self, params, queue):
        """
        Try to discover and resolve a test.

        :param params: dictionary with test parameters.
        :type params: dict
        :param queue: a queue for communicating with the test runner.
        :type queue: an instance of :class:`multiprocessing.Queue`
        :return: a test factory (a pair of test class and test parameters)
        """
        test_name = params.get('id')
        test_path = os.path.abspath(test_name)
        if os.path.exists(test_path):
            path_analyzer = path.PathInspector(test_path)
            if path_analyzer.is_python():
                test_class, test_parameters = self._make_test(test_name,
                                                              test_path,
                                                              params, queue)
            else:
                if os.access(test_path, os.X_OK):
                    test_class, test_parameters = self._make_simple_test(test_path,
                                                                         params)
                else:
                    test_class, test_parameters = self._make_not_a_test(test_path, params)
        else:
            # Try to resolve test ID (keep compatibility)
            rel_path = '%s.py' % test_name
            test_path = os.path.join(data_dir.get_test_dir(), rel_path)
            if os.path.exists(test_path):
                test_class, test_parameters = self._make_test(rel_path,
                                                              test_path,
                                                              params, queue)
            else:
                test_class, test_parameters = self._make_missing_test(
                    test_name, params)
        return test_class, test_parameters

    def discover(self, params_list, queue):
        """
        Discover tests for test suite.

        :param params_list: a list of test parameters.
        :type params_list: list
        :param queue: a queue for communicating with the test runner.
        :type queue: an instance of :class:`multiprocessing.Queue`
        :return: a test suite (a list of test factories).
        """
        test_suite = []
        for params in params_list:
            test_class, test_parameters = self.discover_test(params, queue)
            test_suite.append((test_class, test_parameters))
        return test_suite

    def load_test(self, test_factory):
        """
        Load test from the test factory.

        :param test_factory: a pair of test class and parameters.
        :type params: tuple
        :return: an instance of :class:`avocado.test.Testself`.
        """
        test_class, test_parameters = test_factory
        test_instance = test_class(**test_parameters)
        return test_instance
