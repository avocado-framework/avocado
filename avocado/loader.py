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

import imp
import inspect
import os
import re
import sys

from avocado import test
from avocado.core import data_dir
from avocado.utils import path

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


class _DebugJob(object):

    def __init__(self):
        self.logdir = '.'


class BrokenSymlink(object):
    pass


class AccessDeniedPath(object):
    pass


class TestLoader(object):

    """
    Test loader class.
    """

    def __init__(self, job=None):
        if job is None:
            job = _DebugJob()
        self.job = job

    def _is_unittests_like(self, test_class, pattern='test'):
        for name, _ in inspect.getmembers(test_class, inspect.ismethod):
            if name.startswith(pattern):
                return True
        return False

    def _make_unittests_like(self, test_class, pattern='test'):
        test_methods = []
        for name, obj in inspect.getmembers(test_class, inspect.ismethod):
            if name.startswith(pattern):
                test_methods.append((name, obj))
        return test_methods

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
        test_parameters = {'name': test_path,
                           'base_logdir': self.job.logdir,
                           'params': params,
                           'job': self.job}
        return test_class, test_parameters

    def _make_tests(self, test_name, test_path, params):
        module_name = os.path.basename(test_path).split('.')[0]
        test_module_dir = os.path.dirname(test_path)
        sys.path.append(test_module_dir)
        test_class = None
        test_parameters = {'name': test_name,
                           'base_logdir': self.job.logdir,
                           'params': params,
                           'job': self.job}
        stdin, stdout, stderr = sys.stdin, sys.stdout, sys.stderr
        try:
            sys.stdin = None
            sys.stdout = StringIO.StringIO()
            sys.stderr = StringIO.StringIO()
            f, p, d = imp.find_module(module_name, [test_module_dir])
            test_module = imp.load_module(module_name, f, p, d)
            f.close()
            for name, obj in inspect.getmembers(test_module):
                if inspect.isclass(obj) and inspect.getmodule(obj) == test_module:
                    if issubclass(obj, test.Test):
                        test_class = obj
                        break
            if test_class is not None:
                # Module is importable and does have an avocado test class
                # inside, let's proceed.
                if self._is_unittests_like(test_class):
                    test_factories = []
                    for test_method in self._make_unittests_like(test_class):
                        copy_test_parameters = test_parameters.copy()
                        copy_test_parameters['methodName'] = test_method[0]
                        class_and_method_name = ':%s.%s' % (test_class.__name__, test_method[0])
                        copy_test_parameters['name'] += class_and_method_name
                        test_factories.append([test_class, copy_test_parameters])
                    return test_factories
            else:
                if os.access(test_path, os.X_OK):
                    # Module does not have an avocado test class inside but
                    # it's executable, let's execute it.
                    test_class = test.SimpleTest
                    test_parameters['name'] = test_path
                else:
                    # Module does not have an avocado test class inside, and
                    # it's not executable. Not a Test.
                    test_class = test.NotATest
                    test_parameters['name'] = test_path

        # Since a lot of things can happen here, the broad exception is
        # justified. The user will get it unadulterated anyway, and avocado
        # will not crash.
        except BaseException, details:  # Ugly python files can raise any exc
            if isinstance(details, KeyboardInterrupt):
                raise   # Don't ignore ctrl+c
            if os.access(test_path, os.X_OK):
                # Module can't be imported, and it's executable. Let's try to
                # execute it.
                test_class = test.SimpleTest
                test_parameters['name'] = test_path
            else:
                # Module can't be imported and it's not an executable. Let's
                # see if there's an avocado import into the test. Although
                # not entirely reliable, we hope it'll be good enough.
                likely_avocado_test = False
                with open(test_path, 'r') as test_file_obj:
                    test_contents = test_file_obj.read()
                    # Actual tests will have imports starting on column 0
                    patterns = ['^from avocado.* import', '^import avocado.*']
                    for pattern in patterns:
                        if re.search(pattern, test_contents, re.MULTILINE):
                            likely_avocado_test = True
                            break
                if likely_avocado_test:
                    test_class = test.BuggyTest
                    params['exception'] = details
                else:
                    test_class = test.NotATest
        finally:
            sys.stdin = stdin
            sys.stdout = stdout
            sys.stderr = stderr

        sys.path.pop(sys.path.index(test_module_dir))

        return [(test_class, test_parameters)]

    def discover_tests(self, params):
        """
        Try to discover and resolve tests.

        :param params: dictionary with test parameters.
        :type params: dict
        :return: a list of test factories (a pair of test class and test parameters).
        """
        test_name = test_path = params.get('id')
        if os.path.exists(test_path):
            if os.access(test_path, os.R_OK) is False:
                return [(AccessDeniedPath, {'params': {'id': test_path}})]
            path_analyzer = path.PathInspector(test_path)
            if path_analyzer.is_python():
                test_factories = self._make_tests(test_name,
                                                  test_path,
                                                  params)
                return test_factories
            else:
                if os.access(test_path, os.X_OK):
                    test_class, test_parameters = self._make_simple_test(test_path,
                                                                         params)
                else:
                    test_class, test_parameters = self._make_not_a_test(test_path,
                                                                        params)
        else:
            if os.path.islink(test_path):
                try:
                    if not os.path.isfile(os.readlink(test_path)):
                        return [(BrokenSymlink, {'params': {'id': test_path}})]
                except OSError:
                    return [(AccessDeniedPath, {'params': {'id': test_path}})]

            # Try to resolve test ID (keep compatibility)
            rel_path = '%s.py' % test_name
            test_path = os.path.join(data_dir.get_test_dir(), rel_path)
            if os.path.exists(test_path):
                test_factories = self._make_tests(rel_path, test_path, params)
                return test_factories
            else:
                test_class, test_parameters = self._make_missing_test(
                    test_name, params)
        return [(test_class, test_parameters)]

    def discover_url(self, url):
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
        ignore_suffix = ('.data', '.pyc', '.pyo', '__init__.py',
                         '__main__.py')
        params_list = []

        # Look for filename:test_method pattern
        if ':' in url:
            url, filter_pattern = url.split(':', 1)
        else:
            filter_pattern = None

        def onerror(exception):
            norm_url = os.path.abspath(url)
            norm_error_filename = os.path.abspath(exception.filename)
            if os.path.isdir(norm_url) and norm_url != norm_error_filename:
                omit_non_tests = True
            else:
                omit_non_tests = False

            params_list.append({'id': exception.filename,
                                'filter': filter_pattern,
                                'omit_non_tests': omit_non_tests})

        for dirpath, dirnames, filenames in os.walk(url, onerror=onerror):
            for dir_name in dirnames:
                if dir_name.startswith('.'):
                    dirnames.pop(dirnames.index(dir_name))
            for file_name in filenames:
                if not file_name.startswith('.'):
                    ignore = False
                    for suffix in ignore_suffix:
                        if file_name.endswith(suffix):
                            ignore = True
                    if not ignore:
                        pth = os.path.join(dirpath, file_name)
                        params_list.append({'id': pth,
                                            'omit_non_tests': True})
        return params_list

    def discover_urls(self, urls):
        """
        Discover (possible) tests from test urls.

        :param urls: a list of tests urls.
        :type urls: list
        :return: a list of test params (each one a dictionary).
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
            test_factories = self.discover_tests(params)
            for test_factory in test_factories:
                if test_factory is None:
                    continue
                test_class, test_parameters = test_factory
                if test_class in [test.NotATest, BrokenSymlink, AccessDeniedPath]:
                    if not params.get('omit_non_tests'):
                        test_suite.append((test_class, test_parameters))
                else:
                    test_suite.append((test_class, test_parameters))
        return test_suite

    @staticmethod
    def validate(test_suite):
        """
        Find missing files/non-tests provided by the user in the input.

        Used mostly for user input validation.

        :param test_suite: List with tuples (test_class, test_params)
        :return: list of missing files.
        """
        missing = []
        not_test = []
        broken_symlink = []
        access_denied = []
        for suite in test_suite:
            if suite[0] == test.MissingTest:
                missing.append(suite[1]['params']['id'])
            elif suite[0] == test.NotATest:
                not_test.append(suite[1]['params']['id'])
            elif suite[0] == BrokenSymlink:
                broken_symlink.append(suite[1]['params']['id'])
            elif suite[0] == AccessDeniedPath:
                access_denied.append(suite[1]['params']['id'])

        return missing, not_test, broken_symlink, access_denied

    def validate_ui(self, test_suite, ignore_missing=False,
                    ignore_not_test=False, ignore_broken_symlinks=False,
                    ignore_access_denied=False):
        """
        Validate test suite and deliver error messages to the UI
        :param test_suite: List of tuples (test_class, test_params)
        :type test_suite: list
        :return: List with error messages
        :rtype: list
        """
        (missing, not_test, broken_symlink,
         access_denied) = self.validate(test_suite)
        broken_symlink_msg = ''
        if (not ignore_broken_symlinks) and broken_symlink:
            if len(broken_symlink) == 1:
                broken_symlink_msg = ("Cannot access '%s': Broken symlink" %
                                      ", ".join(broken_symlink))
            elif len(broken_symlink) > 1:
                broken_symlink_msg = ("Cannot access '%s': Broken symlinks" %
                                      ", ".join(broken_symlink))
        access_denied_msg = ''
        if (not ignore_access_denied) and access_denied:
            if len(access_denied) == 1:
                access_denied_msg = ("Cannot access '%s': Access denied" %
                                     ", ".join(access_denied))
            elif len(access_denied) > 1:
                access_denied_msg = ("Cannot access '%s': Access denied" %
                                     ", ".join(access_denied))
        missing_msg = ''
        if (not ignore_missing) and missing:
            if len(missing) == 1:
                missing_msg = ("Cannot access '%s': File not found" %
                               ", ".join(missing))
            elif len(missing) > 1:
                missing_msg = ("Cannot access '%s': Files not found" %
                               ", ".join(missing))
        not_test_msg = ''
        if (not ignore_not_test) and not_test:
            if len(not_test) == 1:
                not_test_msg = ("File '%s' is not an avocado test" %
                                ", ".join(not_test))
            elif len(not_test) > 1:
                not_test_msg = ("Files '%s' are not avocado tests" %
                                ", ".join(not_test))

        return [msg for msg in
                [access_denied_msg, broken_symlink_msg, missing_msg,
                 not_test_msg] if msg]

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
