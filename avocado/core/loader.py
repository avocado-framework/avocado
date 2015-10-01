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

import collections
import imp
import inspect
import os
import re
import sys
import shlex
import fnmatch

from . import data_dir
from . import output
from . import test
from . import exceptions
from .settings import settings
from ..utils import path
from ..utils import stacktrace

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


DEFAULT = False     # Show default tests (for execution)
AVAILABLE = None    # Available tests (for listing purposes)
ALL = True          # All tests (inicluding broken ones)


class LoaderError(Exception):

    """ Loader exception """

    pass


class InvalidLoaderPlugin(LoaderError):

    """ Invalid loader plugin """

    pass


class LoaderUnhandledUrlError(LoaderError):

    """ Urls not handled by any loader """

    def __init__(self, unhandled_urls, plugins):
        super(LoaderUnhandledUrlError, self).__init__()
        self.unhandled_urls = unhandled_urls
        self.plugins = [_.name for _ in plugins]

    def __str__(self):
        return ("Unable to discover url(s) '%s' with loader plugins(s) '%s', "
                "try running 'avocado list -V %s' to see the details."
                % ("', '" .join(self.unhandled_urls),
                   "', '".join(self.plugins),
                   " ".join(self.unhandled_urls)))


class TestLoaderProxy(object):

    def __init__(self):
        self._initialized_plugins = []
        self.registered_plugins = []
        self.url_plugin_mapping = {}
        self._test_types = {}

    def register_plugin(self, plugin):
        try:
            if issubclass(plugin, TestLoader):
                self.registered_plugins.append(plugin)
                for test_type in plugin.get_type_label_mapping().itervalues():
                    if (test_type in self._test_types and
                            self._test_types[test_type] != plugin):
                        msg = ("Multiple plugins using the same test_type not "
                               "yet supported (%s, %s)"
                               % (test_type, self._test_types))
                        raise NotImplementedError(msg)
                    self._test_types[test_type] = plugin
            else:
                raise ValueError
        except ValueError:
            raise InvalidLoaderPlugin("Object %s is not an instance of "
                                      "TestLoader" % plugin)

    def load_plugins(self, args):
        def _err_list_loaders():
            return ("Loaders: %s\nTypes: %s" % (names,
                                                self._test_types.keys()))
        self._initialized_plugins = []
        # Add (default) file loader if not already registered
        if FileLoader not in self.registered_plugins:
            self.register_plugin(FileLoader)
        # Load plugin by the priority from settings
        names = ["@" + _.name for _ in self.registered_plugins]
        loaders = getattr(args, 'loaders', None)
        if not loaders:
            loaders = settings.get_value("plugins", "loaders", list, [])
        if '?' in loaders:
            raise LoaderError("Loaders: %s\nTypes: %s"
                              % (names, self._test_types.keys()))
        if "DEFAULT" in loaders:   # Replace DEFAULT with unused loaders
            idx = loaders.index("DEFAULT")
            loaders = (loaders[:idx] + [_ for _ in names if _ not in loaders] +
                       loaders[idx+1:])
            while "DEFAULT" in loaders:    # Remove duplicite DEFAULT entries
                loaders.remove("DEFAULT")

        loaders = [_.split(':', 1) for _ in loaders]
        priority = [_[0] for _ in loaders]
        for i, name in enumerate(priority):
            extra_params = {}
            if name in names:
                plugin = self.registered_plugins[names.index(name)]
            elif name in self._test_types:
                plugin = self._test_types[name]
                extra_params['allowed_test_types'] = name
            else:
                raise InvalidLoaderPlugin("Loader '%s' not available:\n"
                                          "Loaders: %s\nTypes: %s"
                                          % (name, names,
                                             self._test_types.keys()))
            if len(loaders[i]) == 2:
                extra_params['loader_options'] = loaders[i][1]
            self._initialized_plugins.append(plugin(args, extra_params))

    def get_extra_listing(self):
        for loader_plugin in self._initialized_plugins:
            loader_plugin.get_extra_listing()

    def get_base_keywords(self):
        base_path = []
        for loader_plugin in self._initialized_plugins:
            base_path += loader_plugin.get_base_keywords()
        return base_path

    def get_type_label_mapping(self):
        mapping = {}
        for loader_plugin in self._initialized_plugins:
            mapping.update(loader_plugin.get_type_label_mapping())
        return mapping

    def get_decorator_mapping(self):
        mapping = {}
        for loader_plugin in self._initialized_plugins:
            mapping.update(loader_plugin.get_decorator_mapping())
        return mapping

    def discover(self, urls, list_tests=False):
        """
        Discover (possible) tests from test urls.

        :param urls: a list of tests urls; if [] use plugin defaults
        :type urls: builtin.list
        :param list_tests: Limit tests to be displayed (loader.ALL|DEFAULT...)
        :return: A list of test factories (tuples (TestClass, test_params))
        """
        def handle_exception(plugin, details):
            # FIXME: Introduce avocado.exceptions logger and use here
            stacktrace.log_message("Test discovery plugin %s failed: "
                                   "%s" % (plugin, details),
                                   'avocado.app.exceptions')
            # FIXME: Introduce avocado.traceback logger and use here
            stacktrace.log_exc_info(sys.exc_info(),
                                    'avocado.app.tracebacks')
        tests = []
        unhandled_urls = []
        if not urls:
            for loader_plugin in self._initialized_plugins:
                try:
                    tests.extend(loader_plugin.discover(None, list_tests))
                except Exception, details:
                    handle_exception(loader_plugin, details)
        else:
            for url in urls:
                handled = False
                for loader_plugin in self._initialized_plugins:
                    try:
                        _test = loader_plugin.discover(url, list_tests)
                        if _test:
                            tests.extend(_test)
                            handled = True
                            if not list_tests:
                                break    # Don't process other plugins
                    except Exception, details:
                        handle_exception(loader_plugin, details)
                if not handled:
                    unhandled_urls.append(url)
        if unhandled_urls:
            if list_tests:
                tests.extend([(test.MissingTest, {'name': url})
                              for url in unhandled_urls])
            else:
                raise LoaderUnhandledUrlError(unhandled_urls,
                                              self._initialized_plugins)
        return tests

    def load_test(self, test_factory):
        """
        Load test from the test factory.

        :param test_factory: a pair of test class and parameters.
        :type params: tuple
        :return: an instance of :class:`avocado.core.test.Test`.
        """
        test_class, test_parameters = test_factory
        test_instance = test_class(**test_parameters)
        return test_instance


class TestLoader(object):

    """
    Base for test loader classes
    """

    def __init__(self, args, extra_params):    # pylint: disable=W0613
        self.args = args

    def get_extra_listing(self):
        pass

    @staticmethod
    def get_type_label_mapping():
        """
        Get label mapping for display in test listing.

        :return: Dict {TestClass: 'TEST_LABEL_STRING'}
        """
        raise NotImplementedError

    @staticmethod
    def get_decorator_mapping():
        """
        Get label mapping for display in test listing.

        :return: Dict {TestClass: decorator function}
        """
        raise NotImplementedError

    def discover(self, url, list_tests=DEFAULT):
        """
        Discover (possible) tests from an url.

        :param url: the url to be inspected.
        :type url: str
        :return: a list of test matching the url as params.
        """
        raise NotImplementedError


class BrokenSymlink(object):

    """ Dummy object to represent url pointing to a BrokenSymlink path """

    pass


class AccessDeniedPath(object):

    """ Dummy object to represent url pointing to a inaccessible path """

    pass


class FilteredOut(object):

    """ Dummy object to represent test filtered out by the optional mask """

    pass


def add_file_loader_options(parser):
    loader = parser.add_argument_group('loader options')
    loader.add_argument('--loaders', nargs='*', help="Overrides the priority "
                        "of the test loaders. You can specify either "
                        "@loader_name or TEST_TYPE. By default it tries all "
                        "available loaders according to priority set in "
                        "settings->plugins.loaders.")
    loader.add_argument('--inner-runner', default=None,
                        metavar='EXECUTABLE',
                        help=('Path to an specific test runner that '
                              'allows the use of its own tests. This '
                              'should be used for running tests that '
                              'do not conform to Avocado\' SIMPLE test'
                              'interface and can not run standalone'))

    chdir_help = ('Change directory before executing tests. This option '
                  'may be necessary because of requirements and/or '
                  'limitations of the inner test runner. If the inner '
                  'runner requires to be run from its own base directory,'
                  'use "runner" here. If the inner runner runs tests based'
                  ' on files and requires to be run from the directory '
                  'where those files are located, use "test" here and '
                  'specify the test directory with the option '
                  '"--inner-runner-testdir". Defaults to "%(default)s"')
    loader.add_argument('--inner-runner-chdir', default='off',
                        choices=('runner', 'test', 'off'),
                        help=chdir_help)

    loader.add_argument('--inner-runner-testdir', metavar='DIRECTORY',
                        default=None,
                        help=('Where test files understood by the inner'
                              ' test runner are located in the '
                              'filesystem. Obviously this assumes and '
                              'only applies to inner test runners that '
                              'run tests from files'))


class FileLoader(TestLoader):

    """
    Test loader class.
    """

    name = 'file'

    def __init__(self, args, extra_params):
        super(FileLoader, self).__init__(args, extra_params)
        loader_options = extra_params.get('loader_options')
        if loader_options == '?':
            raise LoaderError("File loader accept option to sets the "
                              "inner-runner executable.")
        self._inner_runner = self._process_inner_runner(args, loader_options)
        self.test_type = extra_params.get('allowed_test_types')

    @staticmethod
    def _process_inner_runner(args, extra_params):
        """ Enables the inner_runner when asked for """
        runner = getattr(args, 'inner_runner', None)
        chdir = getattr(args, 'inner_runner_chdir', 'off')
        test_dir = getattr(args, 'inner_runner_testdir', None)
        if extra_params:
            if runner:
                msg = ("Inner runner specified via booth: --loaders (%s) and "
                       "--inner-runner (%s). Please use only one of them"
                       % (extra_params, runner))
                raise LoaderError(msg)
            runner = extra_params

        if runner:
            inner_runner_and_args = shlex.split(runner)
            if len(inner_runner_and_args) > 1:
                executable = inner_runner_and_args[0]
            else:
                executable = runner
            if not os.path.exists(executable):
                msg = ('Could not find the inner runner executable "%s"'
                       % executable)
                raise LoaderError(msg)
            if chdir == 'test':
                if not test_dir:
                    msg = ('Option "--inner-runner-chdir=test" requires '
                           '"--inner-runner-testdir" to be set.')
                    raise LoaderError(msg)
            elif test_dir:
                msg = ('Option "--inner-runner-testdir" requires '
                       '"--inner-runner-chdir=test".')
                raise LoaderError(msg)

            cls_inner_runner = collections.namedtuple('InnerRunner',
                                                      ['runner', 'chdir',
                                                       'test_dir'])
            return cls_inner_runner(runner, chdir, test_dir)

        elif chdir != "off":
            msg = ('Option "--inner-runner-chdir" requires '
                   '"--inner-runner" to be set.')
            raise LoaderError(msg)
        elif test_dir:
            msg = ('Option "--inner-runner-test-dir" requires '
                   '"--inner-runner" to be set.')
            raise LoaderError(msg)

    @staticmethod
    def get_type_label_mapping():
        return {test.SimpleTest: 'SIMPLE',
                test.InnerRunnerTest: 'INNER_RUNNER',
                test.BuggyTest: 'BUGGY',
                test.NotATest: 'NOT_A_TEST',
                test.MissingTest: 'MISSING',
                BrokenSymlink: 'BROKEN_SYMLINK',
                AccessDeniedPath: 'ACCESS_DENIED',
                test.Test: 'INSTRUMENTED',
                FilteredOut: 'FILTERED'}

    @staticmethod
    def get_decorator_mapping():
        term_support = output.TermSupport()
        return {test.SimpleTest: term_support.healthy_str,
                test.InnerRunnerTest: term_support.healthy_str,
                test.BuggyTest: term_support.fail_header_str,
                test.NotATest: term_support.warn_header_str,
                test.MissingTest: term_support.fail_header_str,
                BrokenSymlink: term_support.fail_header_str,
                AccessDeniedPath: term_support.fail_header_str,
                test.Test: term_support.healthy_str,
                FilteredOut: term_support.warn_header_str}

    def discover(self, url, list_tests=DEFAULT):
        """
        Discover (possible) tests from a directory.

        Recursively walk in a directory and find tests params.
        The tests are returned in alphabetic order.

        Afterwards when "allowed_test_types" is supplied it verifies if all
        found tests are of the allowed type. If not return None (even on
        partial match).

        :param url: the directory path to inspect.
        :param list_tests: list corrupted/invalid tests too
        :return: list of matching tests
        """
        tests = self._discover(url, list_tests)
        if self.test_type:
            mapping = self.get_type_label_mapping()
            if self.test_type == 'INSTRUMENTED':
                # Instrumented is parent of all of supported tests, we need to
                # exclude the rest of the supported tests
                filtered_clss = tuple(_ for _ in mapping.iterkeys()
                                      if _ is not test.Test)
                for tst in tests:
                    if (not issubclass(tst[0], test.Test) or
                            issubclass(tst[0], filtered_clss)):
                        return None
            else:
                test_class = (key for key, value in mapping.iteritems()
                              if value == self.test_type).next()
                for tst in tests:
                    if not issubclass(tst[0], test_class):
                        return None
        return tests

    def _discover(self, url, list_tests=DEFAULT):
        """
        Recursively walk in a directory and find tests params.
        The tests are returned in alphabetic order.

        :param url: the directory path to inspect.
        :param list_tests: list corrupted/invalid tests too
        :return: list of matching tests
        """
        if self._inner_runner:
            return self._make_inner_runner_test(url)

        if url is None:
            if list_tests is DEFAULT:
                return []   # Return empty set when not listing details
            else:
                url = data_dir.get_test_dir()
        ignore_suffix = ('.data', '.pyc', '.pyo', '__init__.py',
                         '__main__.py')

        # Look for filename:test_method pattern
        subtests_filter = None
        if ':' in url:
            _url, _subtests_filter = url.split(':', 1)
            if os.path.exists(_url):    # otherwise it's ':' in the file name
                url = _url
                subtests_filter = _subtests_filter

        if not os.path.isdir(url):  # Single file
            return self._make_tests(url, list_tests, subtests_filter)

        tests = []

        def add_test_from_exception(exception):
            """ If the exc.filename is valid test it's added to tests """
            tests.extend(self._make_tests(exception.filename, list_tests))

        def skip_non_test(exception):
            """ Always return None """
            return None

        if list_tests:      # ALL => include everything
            onerror = add_test_from_exception
        else:               # DEFAULT, AVAILABLE => skip missing tests
            onerror = skip_non_test

        for dirpath, _, filenames in os.walk(url, onerror=onerror):
            for file_name in filenames:
                if not file_name.startswith('.'):
                    for suffix in ignore_suffix:
                        if file_name.endswith(suffix):
                            break
                    else:
                        pth = os.path.join(dirpath, file_name)
                        tests.extend(self._make_tests(pth, list_tests))
        return tests

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

    def _make_avocado_tests(self, test_path, make_broken, subtests_filter,
                            test_name=None):
        if test_name is None:
            test_name = test_path
        module_name = os.path.basename(test_path).split('.')[0]
        test_module_dir = os.path.dirname(test_path)
        sys.path.insert(0, test_module_dir)
        stdin, stdout, stderr = sys.stdin, sys.stdout, sys.stderr
        try:
            sys.stdin = None
            sys.stdout = StringIO.StringIO()
            sys.stderr = StringIO.StringIO()
            f, p, d = imp.find_module(module_name, [test_module_dir])
            test_module = imp.load_module(module_name, f, p, d)
            f.close()
            for _, obj in inspect.getmembers(test_module):
                if (inspect.isclass(obj) and
                        inspect.getmodule(obj) == test_module):
                    if issubclass(obj, test.Test):
                        test_class = obj
                        break
            else:
                if os.access(test_path, os.X_OK):
                    # Module does not have an avocado test class inside but
                    # it's executable, let's execute it.
                    return self._make_test(test.SimpleTest, test_path)
                else:
                    # Module does not have an avocado test class inside, and
                    # it's not executable. Not a Test.
                    return make_broken(test.NotATest, test_path)
            if test_class is not None:
                # Module is importable and does have an avocado test class
                # inside, let's proceed.
                if self._is_unittests_like(test_class):
                    test_factories = []
                    test_parameters = {'name': test_name}
                    if subtests_filter:
                        test_parameters['params'] = {'filter': subtests_filter}
                    for test_method in self._make_unittests_like(test_class):
                        name = test_name + ':%s.%s' % (test_class.__name__,
                                                       test_method[0])
                        if (subtests_filter is not None and
                                not fnmatch.fnmatch(test_method[0],
                                                    subtests_filter)):
                            test_factories.extend(make_broken(FilteredOut,
                                                              name))
                        else:
                            tst = (test_class, {'name': name,
                                                'methodName': test_method[0]})
                            test_factories.append(tst)
                    return test_factories
                else:
                    return self._make_test(test_class, test_name)

        # Since a lot of things can happen here, the broad exception is
        # justified. The user will get it unadulterated anyway, and avocado
        # will not crash.
        except BaseException, details:  # Ugly python files can raise any exc
            if isinstance(details, KeyboardInterrupt):
                raise   # Don't ignore ctrl+c
            if os.access(test_path, os.X_OK):
                # Module can't be imported, and it's executable. Let's try to
                # execute it.
                return self._make_test(test.SimpleTest, test_path)
            else:
                # Module can't be imported and it's not an executable. Let's
                # see if there's an avocado import into the test. Although
                # not entirely reliable, we hope it'll be good enough.
                with open(test_path, 'r') as test_file_obj:
                    test_contents = test_file_obj.read()
                    # Actual tests will have imports starting on column 0
                    patterns = ['^from avocado.* import', '^import avocado.*']
                    for pattern in patterns:
                        if re.search(pattern, test_contents, re.MULTILINE):
                            break
                    else:
                        return make_broken(test.NotATest, test_path)
                    return make_broken(test.BuggyTest, test_path,
                                       {'exception': details})
        finally:
            sys.stdin = stdin
            sys.stdout = stdout
            sys.stderr = stderr
            sys.path.remove(test_module_dir)

    @staticmethod
    def _make_test(klass, uid, params=None):
        """
        Create test template
        :param klass: test class
        :param uid: test uid (by default used as id and name)
        :param params: optional params (id won't be overriden when present)
        """
        if not params:
            params = {}
        params.setdefault('id', uid)
        return [(klass, {'name': uid, 'params': params})]

    def _make_inner_runner_test(self, test_path):
        """
        Creates inner-runner test (adds self._inner_runner as test argument)
        """
        tst = self._make_test(test.InnerRunnerTest, test_path)
        tst[0][1]['inner_runner'] = self._inner_runner
        return tst

    def _make_tests(self, test_path, list_non_tests, subtests_filter=None):
        """
        Create test templates from given path
        :param test_path: File system path
        :param list_non_tests: include bad tests (NotATest, BrokenSymlink,...)
        :param subtests_filter: optional filter of methods for avocado tests
        """
        def ignore_broken(klass, uid, params=None):
            """ Always return empty list """
            return []

        if list_non_tests:   # return broken test with params
            make_broken = self._make_test
        else:               # return empty set instead
            make_broken = ignore_broken
        test_name = test_path
        if os.path.exists(test_path):
            if os.access(test_path, os.R_OK) is False:
                return make_broken(AccessDeniedPath, test_path)
            path_analyzer = path.PathInspector(test_path)
            if path_analyzer.is_python():
                return self._make_avocado_tests(test_path, make_broken,
                                                subtests_filter)
            else:
                if os.access(test_path, os.X_OK):
                    return self._make_test(test.SimpleTest, test_path)
                else:
                    return make_broken(test.NotATest, test_path)
        else:
            if os.path.islink(test_path):
                try:
                    if not os.path.isfile(os.readlink(test_path)):
                        return make_broken(BrokenSymlink, test_path)
                except OSError:
                    return make_broken(AccessDeniedPath, test_path)

            # Try to resolve test ID (keep compatibility)
            rel_path = '%s.py' % test_name
            test_path = os.path.join(data_dir.get_test_dir(), rel_path)
            if os.path.exists(test_path):
                return self._make_avocado_tests(test_path, list_non_tests,
                                                subtests_filter, rel_path)
            else:
                return make_broken(test.MissingTest, test_name)


loader = TestLoaderProxy()
