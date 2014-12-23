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

from avocado import test
from avocado.core import data_dir
from avocado.utils import path


class _DebugJob(object):

    def __init__(self):
        self.logdir = '.'


class TestLoader(object):

    """
    Test loader class.
    """

    def __init__(self, job=None):
        if job is None:
            job = _DebugJob()
        self.job = job

    def _make_missing_test(self, test_name, params):
        test_class = test.MissingTest
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

    def _make_test(self, test_name, test_path, params):
        module_name = os.path.basename(test_path).split('.')[0]
        test_module_dir = os.path.dirname(test_path)
        try:
            f, p, d = imp.find_module(module_name, [test_module_dir])
            test_module = imp.load_module(module_name, f, p, d)
            f.close()
            test_class = getattr(test_module, module_name)
        except ImportError:
            test_class = test.MissingTest
        finally:
            test_parameters = {'name': test_name,
                               'base_logdir': self.job.logdir,
                               'params': params,
                               'job': self.job}
        return test_class, test_parameters

    def discover_test(self, params):
        """
        Try to discover and resolve a test.

        :param params: dictionary with test parameters.
        :type params: dict
        :return: a test factory (a pair of test class and test parameters)
        """
        test_name = params.get('id')
        test_path = os.path.abspath(test_name)
        if os.path.exists(test_path):
            path_analyzer = path.PathInspector(test_path)
            if path_analyzer.is_python():
                test_class, test_parameters = self._make_test(test_name,
                                                              test_path,
                                                              params)
            elif os.access(test_path, os.X_OK):
                test_class, test_parameters = self._make_simple_test(test_path,
                                                                     params)
            else:
                test_class, test_parameters = self._make_missing_test(test_name,
                                                                      params)
        else:
            # Try to resolve test ID (keep compatibility)
            rel_path = '%s.py' % test_name
            test_path = os.path.join(data_dir.get_test_dir(), rel_path)
            if os.path.exists(test_path):
                test_class, test_parameters = self._make_test(rel_path,
                                                              test_path,
                                                              params)
            else:
                test_class, test_parameters = self._make_missing_test(
                    test_name, params)
        return test_class, test_parameters

    def discover_directory(self, dir_path='.', ignore_suffix=None):
        """
        Discover (possible) tests from a directory.

        Recursively walk in a directory and find tests params.
        The tests are returned in alphabetic order.

        :param dir_path: the directory path to inspect.
        :type dir_path: str
        :param ignore_suffix: list of suffix to ignore in paths.
        :type ignore_suffix: list
        :return: a list of test params (each one a dictionary).
        """
        if ignore_suffix is None:
            ignore_suffix = ('.data', '.pyc', '.pyo')
        entries = sorted(os.listdir(os.path.abspath(dir_path)))
        params_list = []
        for entry in entries:
            new_path = os.path.join(dir_path, entry)
            if entry.startswith('.'):
                continue
            elif entry.endswith(ignore_suffix):
                continue
            elif os.path.isdir(new_path):
                params_list.extend(self.discover_directory(new_path))
            else:
                params_list.append({'id': new_path})
        return params_list

    def discover_url(self, url):
        """
        Discover (possible) test from test url.

        :params url: the test url to discover.
        :type url: str
        :return: a list of test params (each one a dictionary).
        """
        if os.path.isdir(os.path.abspath(url)):
            params_list = self.discover_directory(url)
            if params_list:
                return params_list
            else:
                return []
        else:
            return [{'id': url}]

    def discover_urls(self, urls):
        """
        Discover (possible) tests from test urls.

        :param urls: a list of tests urls.
        :type urls: list
        :return: a list of test params (each one a dictioanry).
        """
        params_list = []
        for url in urls:
            if url == '':
                continue
            params_list.extend(self.discover_url(url))
        return params_list

    def discover(self, params_list):
        """
        Discover tests for test suite.

        :param params_list: a list of test parameters.
        :type params_list: list
        :return: a test suite (a list of test factories).
        """
        test_suite = []
        for params in params_list:
            test_class, test_parameters = self.discover_test(params)
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
