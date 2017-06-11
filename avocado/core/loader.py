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

import ast
import collections
import imp
import inspect
import os
import re
import shlex
import sys

from . import data_dir
from . import output
from . import test
from . import safeloader
from ..utils import path
from ..utils import stacktrace
from .settings import settings
from .output import LOG_UI

#: Show default tests (for execution)
DEFAULT = False
#: Available tests (for listing purposes)
AVAILABLE = None
#: All tests (including broken ones)
ALL = True


class MissingTest(object):
    """
    Class representing reference which failed to be discovered
    """


def filter_test_tags(test_suite, filter_by_tags, include_empty=False):
    """
    Filter the existing (unfiltered) test suite based on tags

    The filtering mechanism is agnostic to test type.  It means that
    if users request filtering by tag and the specific test type does
    not populate the test tags, it will be considered to have empty
    tags.

    :param test_suite: the unfiltered test suite
    :type test_suite: dict
    :param filter_by_tags: the list of tag sets to use as filters
    :type filter_by_tags: list of comma separated tags (['foo,bar', 'fast'])
    :param include_empty: if true tests without tags will not be filtered out
    :type include_empty: bool
    """
    filtered = []
    for klass, info in test_suite:
        test_tags = info.get('tags', set([]))
        if not test_tags and include_empty:
            filtered.append((klass, info))
            continue

        for raw_tags in filter_by_tags:
            required_tags = raw_tags.split(',')
            must_not_have_tags = set([_[1:] for _ in required_tags
                                      if _.startswith('-')])
            if must_not_have_tags.intersection(test_tags):
                continue

            must_have_tags = set([_ for _ in required_tags
                                  if not _.startswith('-')])
            if must_have_tags:
                if not must_have_tags.issubset(test_tags):
                    continue

            filtered.append((klass, info))
            break

    return filtered


class LoaderError(Exception):

    """ Loader exception """

    pass


class InvalidLoaderPlugin(LoaderError):

    """ Invalid loader plugin """

    pass


class LoaderUnhandledReferenceError(LoaderError):

    """ Test References not handled by any resolver """

    def __init__(self, unhandled_references, plugins):
        super(LoaderUnhandledReferenceError, self).__init__()
        self.unhandled_references = unhandled_references
        self.plugins = [_.name for _ in plugins]

    def __str__(self):
        return ("Unable to resolve reference(s) '%s' with plugins(s) '%s', "
                "try running 'avocado list -V %s' to see the details."
                % ("', '" .join(self.unhandled_references),
                   "', '".join(self.plugins),
                   " ".join(self.unhandled_references)))


class TestLoaderProxy(object):

    def __init__(self):
        self._initialized_plugins = []
        self.registered_plugins = []
        self.reference_plugin_mapping = {}
        self._label_mapping = None
        self._decorator_mapping = None

    def register_plugin(self, plugin):
        try:
            if issubclass(plugin, TestLoader):
                if plugin not in self.registered_plugins:
                    self.registered_plugins.append(plugin)
            else:
                raise ValueError
        except ValueError:
            raise InvalidLoaderPlugin("Object %s is not an instance of "
                                      "TestLoader" % plugin)

    def load_plugins(self, args):
        def _good_test_types(plugin):
            """
            List all supported test types (excluding incorrect ones)
            """
            name = plugin.name
            mapping = plugin.get_type_label_mapping()
            # Using __func__ to avoid problem with different term_supp instances
            healthy_func = getattr(output.TERM_SUPPORT.healthy_str, '__func__')
            types = [mapping[_[0]]
                     for _ in plugin.get_decorator_mapping().iteritems()
                     if _[1].__func__ is healthy_func]
            return [name + '.' + _ for _ in types]

        def _str_loaders():
            """
            :return: string of sorted loaders and types
            """
            out = ""
            for plugin in self.registered_plugins:
                out += "  %s: %s\n" % (plugin.name,
                                       ", ".join(_good_test_types(plugin)))
            return out.rstrip('\n')

        self._initialized_plugins = []
        # Add (default) file loader if not already registered
        if FileLoader not in self.registered_plugins:
            self.register_plugin(FileLoader)
        if ExternalLoader not in self.registered_plugins:
            self.register_plugin(ExternalLoader)
        # Register external runner when --external-runner is used
        if getattr(args, "external_runner", None):
            self.register_plugin(ExternalLoader)
            args.loaders = ["external:%s" % args.external_runner]
        supported_loaders = [_.name for _ in self.registered_plugins]
        supported_types = []
        for plugin in self.registered_plugins:
            supported_types.extend(_good_test_types(plugin))
        # Load plugin by the priority from settings
        loaders = getattr(args, 'loaders', None)
        if not loaders:
            loaders = settings.get_value("plugins", "loaders", list, [])
        if '?' in loaders:
            raise LoaderError("Available loader plugins:\n%s" % _str_loaders())
        if "@DEFAULT" in loaders:  # Replace @DEFAULT with unused loaders
            idx = loaders.index("@DEFAULT")
            loaders = (loaders[:idx] + [plugin for plugin in supported_loaders
                                        if plugin not in loaders] +
                       loaders[idx + 1:])
            while "@DEFAULT" in loaders:  # Remove duplicate @DEFAULT entries
                loaders.remove("@DEFAULT")

        loaders = [_.split(':', 1) for _ in loaders]
        priority = [_[0] for _ in loaders]
        for i, name in enumerate(priority):
            extra_params = {}
            if name in supported_types:
                name, extra_params['allowed_test_types'] = name.split('.', 1)
            elif name not in supported_loaders:
                raise InvalidLoaderPlugin("Unknown loader '%s'. Available "
                                          "plugins are:\n%s"
                                          % (name, _str_loaders()))
            if len(loaders[i]) == 2:
                extra_params['loader_options'] = loaders[i][1]
            plugin = self.registered_plugins[supported_loaders.index(name)]
            self._initialized_plugins.append(plugin(args, extra_params))
        self._update_mappings()

    def _update_mappings(self):
        """
        Update the mappings according the current initialized plugins
        """
        # Plugins are initialized, let's update mappings
        self._label_mapping = {MissingTest: "MISSING"}
        for plugin in self._initialized_plugins:
            self._label_mapping.update(plugin.get_type_label_mapping())
        self._decorator_mapping = {MissingTest:
                                   output.TERM_SUPPORT.fail_header_str}
        for plugin in self._initialized_plugins:
            self._decorator_mapping.update(plugin.get_decorator_mapping())

    def get_extra_listing(self):
        for loader_plugin in self._initialized_plugins:
            loader_plugin.get_extra_listing()

    def get_base_keywords(self):
        base_path = []
        for loader_plugin in self._initialized_plugins:
            base_path += loader_plugin.get_base_keywords()
        return base_path

    def get_type_label_mapping(self):
        return self._label_mapping

    def get_decorator_mapping(self):
        return self._decorator_mapping

    def discover(self, references, which_tests=DEFAULT, force=None):
        """
        Discover (possible) tests from test references.

        :param references: a list of tests references; if [] use plugin defaults
        :type references: builtin.list
        :param which_tests: Limit tests to be displayed (ALL, AVAILABLE or
                            DEFAULT)
        :param force: don't raise an exception when some test references
                      are not resolved to tests.
        :return: A list of test factories (tuples (TestClass, test_params))
        """
        def handle_exception(plugin, details):
            # FIXME: Introduce avocado.exceptions logger and use here
            stacktrace.log_message("Test discovery plugin %s failed: "
                                   "%s" % (plugin, details),
                                   LOG_UI.getChild("exceptions"))
            # FIXME: Introduce avocado.traceback logger and use here
            stacktrace.log_exc_info(sys.exc_info(), LOG_UI.getChild("debug"))
        tests = []
        unhandled_references = []
        if not references:
            for loader_plugin in self._initialized_plugins:
                try:
                    tests.extend(loader_plugin.discover(None, which_tests))
                except Exception as details:
                    handle_exception(loader_plugin, details)
        else:
            for reference in references:
                handled = False
                for loader_plugin in self._initialized_plugins:
                    try:
                        _test = loader_plugin.discover(reference, which_tests)
                        if _test:
                            tests.extend(_test)
                            handled = True
                            if not which_tests:
                                break  # Don't process other plugins
                    except Exception as details:
                        handle_exception(loader_plugin, details)
                if not handled:
                    unhandled_references.append(reference)
        if unhandled_references:
            if which_tests:
                tests.extend([(MissingTest, {'name': reference})
                              for reference in unhandled_references])
            else:
                if force == 'on':
                    LOG_UI.error(LoaderUnhandledReferenceError(unhandled_references,
                                                               self._initialized_plugins))
                else:
                    raise LoaderUnhandledReferenceError(unhandled_references,
                                                        self._initialized_plugins)
        return tests

    def load_test(self, test_factory):
        """
        Load test from the test factory.

        :param test_factory: a pair of test class and parameters.
        :type test_factory: tuple
        :return: an instance of :class:`avocado.core.test.Test`.
        """
        test_class, test_parameters = test_factory
        # discard tags, as they are *not* intended to be parameters
        # for the test, but used previously during filtering
        if 'tags' in test_parameters:
            del(test_parameters['tags'])
        if 'modulePath' in test_parameters:
            test_path = test_parameters.pop('modulePath')
        else:
            test_path = None
        if isinstance(test_class, str):
            module_name = os.path.basename(test_path).split('.')[0]
            test_module_dir = os.path.abspath(os.path.dirname(test_path))
            # Tests with local dir imports need this
            try:
                sys.path.insert(0, test_module_dir)
                f, p, d = imp.find_module(module_name, [test_module_dir])
                test_module = imp.load_module(module_name, f, p, d)
            except:
                # On load_module exception we fake the test class and pass
                # the exc_info as parameter to be logged.
                test_parameters['methodName'] = 'test'
                exception = stacktrace.prepare_exc_info(sys.exc_info())
                test_parameters['exception'] = exception
                return test.TestError(**test_parameters)
            finally:
                if test_module_dir in sys.path:
                    sys.path.remove(test_module_dir)
            for _, obj in inspect.getmembers(test_module):
                if (inspect.isclass(obj) and obj.__name__ == test_class and
                        inspect.getmodule(obj) == test_module):
                    if issubclass(obj, test.Test):
                        test_class = obj
                        break
        test_instance = test_class(**test_parameters)

        return test_instance

    def clear_plugins(self):
        self.registered_plugins = []


class TestLoader(object):

    """
    Base for test loader classes
    """

    name = None     # Human friendly name of the loader

    def __init__(self, args, extra_params):  # pylint: disable=W0613
        if "allowed_test_types" in extra_params:
            mapping = self.get_type_label_mapping()
            types = extra_params.pop("allowed_test_types")
            if len(mapping) != 1:
                msg = ("Loader '%s' supports multiple test types but does not "
                       "handle the 'allowed_test_types'. Either don't use "
                       "'%s' instead of '%s.%s' or take care of the "
                       "'allowed_test_types' in the plugin."
                       % (self.name, self.name, self.name, types))
                raise LoaderError(msg)
            elif mapping.itervalues().next() != types:
                raise LoaderError("Loader '%s' doesn't support test type '%s',"
                                  " it supports only '%s'"
                                  % (self.name, types,
                                     mapping.itervalues().next()))
        if "loader_options" in extra_params:
            raise LoaderError("Loader '%s' doesn't support 'loader_options', "
                              "please don't use --loader %s:%s"
                              % (self.name, self.name,
                                 extra_params.get("loader_options")))
        if extra_params:
            raise LoaderError("Loader '%s' doesn't handle extra params %s, "
                              "please adjust your plugin to take care of them."
                              % (self.name, extra_params))
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

    def discover(self, reference, which_tests=DEFAULT):
        """
        Discover (possible) tests from an reference.

        :param reference: the reference to be inspected.
        :type reference: str
        :param which_tests: Limit tests to be displayed (ALL, AVAILABLE or
                            DEFAULT)
        :return: a list of test matching the reference as params.
        """
        raise NotImplementedError


class BrokenSymlink(object):

    """ Dummy object to represent reference pointing to a BrokenSymlink path """

    pass


class AccessDeniedPath(object):

    """ Dummy object to represent reference pointing to a inaccessible path """

    pass


def add_loader_options(parser):
    arggrp = parser.add_argument_group('loader options')
    arggrp.add_argument('--loaders', nargs='*', help="Overrides the priority "
                        "of the test loaders. You can specify either "
                        "@loader_name or TEST_TYPE. By default it tries all "
                        "available loaders according to priority set in "
                        "settings->plugins.loaders.")
    arggrp.add_argument('--external-runner', default=None,
                        metavar='EXECUTABLE',
                        help=('Path to an specific test runner that '
                              'allows the use of its own tests. This '
                              'should be used for running tests that '
                              'do not conform to Avocado\' SIMPLE test'
                              'interface and can not run standalone. Note: '
                              'the use of --external-runner overwrites the --'
                              'loaders to "external_runner"'))

    chdir_help = ('Change directory before executing tests. This option '
                  'may be necessary because of requirements and/or '
                  'limitations of the external test runner. If the external '
                  'runner requires to be run from its own base directory,'
                  'use "runner" here. If the external runner runs tests based'
                  ' on files and requires to be run from the directory '
                  'where those files are located, use "test" here and '
                  'specify the test directory with the option '
                  '"--external-runner-testdir". Defaults to "%(default)s"')
    arggrp.add_argument('--external-runner-chdir', default=None,
                        choices=('runner', 'test'),
                        help=chdir_help)

    arggrp.add_argument('--external-runner-testdir', metavar='DIRECTORY',
                        default=None,
                        help=('Where test files understood by the external'
                              ' test runner are located in the '
                              'filesystem. Obviously this assumes and '
                              'only applies to external test runners that '
                              'run tests from files'))


class NotATest(object):
    """
    Class representing something that is not a test
    """


class FileLoader(TestLoader):

    """
    Test loader class.
    """

    name = 'file'
    __not_test_str = ("Does not look like an INSTRUMENTED test, nor is it "
                      "executable")

    def __init__(self, args, extra_params):
        test_type = extra_params.pop('allowed_test_types', None)
        super(FileLoader, self).__init__(args, extra_params)
        self.test_type = test_type

    @staticmethod
    def get_type_label_mapping():
        return {test.SimpleTest: 'SIMPLE',
                NotATest: 'NOT_A_TEST',
                MissingTest: 'MISSING',
                BrokenSymlink: 'BROKEN_SYMLINK',
                AccessDeniedPath: 'ACCESS_DENIED',
                test.Test: 'INSTRUMENTED'}

    @staticmethod
    def get_decorator_mapping():
        return {test.SimpleTest: output.TERM_SUPPORT.healthy_str,
                NotATest: output.TERM_SUPPORT.warn_header_str,
                MissingTest: output.TERM_SUPPORT.fail_header_str,
                BrokenSymlink: output.TERM_SUPPORT.fail_header_str,
                AccessDeniedPath: output.TERM_SUPPORT.fail_header_str,
                test.Test: output.TERM_SUPPORT.healthy_str}

    def discover(self, reference, which_tests=DEFAULT):
        """
        Discover (possible) tests from a directory.

        Recursively walk in a directory and find tests params.
        The tests are returned in alphabetic order.

        Afterwards when "allowed_test_types" is supplied it verifies if all
        found tests are of the allowed type. If not return None (even on
        partial match).

        :param reference: the directory path to inspect.
        :param which_tests: Limit tests to be displayed (ALL, AVAILABLE or
                            DEFAULT)
        :return: list of matching tests
        """
        tests = self._discover(reference, which_tests)
        if self.test_type:
            mapping = self.get_type_label_mapping()
            if self.test_type == 'INSTRUMENTED':
                # Instrumented tests are defined as string and loaded at the
                # execution time.
                for tst in tests:
                    if not isinstance(tst[0], str):
                        return None
            else:
                test_class = (key for key, value in mapping.iteritems()
                              if value == self.test_type).next()
                for tst in tests:
                    if (isinstance(tst[0], str) or
                            not issubclass(tst[0], test_class)):
                        return None
        return tests

    def _discover(self, reference, which_tests=DEFAULT):
        """
        Recursively walk in a directory and find tests params.
        The tests are returned in alphabetic order.

        :param reference: the directory path to inspect.
        :param which_tests: Limit tests to be displayed (ALL, AVAILABLE or
                            DEFAULT)
        :return: list of matching tests
        """
        if reference is None:
            if which_tests is DEFAULT:
                return []  # Return empty set when not listing details
            else:
                reference = data_dir.get_test_dir()
        ignore_suffix = ('.data', '.pyc', '.pyo', '__init__.py',
                         '__main__.py')

        # Look for filename:test_method pattern
        subtests_filter = None
        if ':' in reference:
            _reference, _subtests_filter = reference.split(':', 1)
            if os.path.exists(_reference):  # otherwise it's ':' in the file name
                reference = _reference
                subtests_filter = re.compile(_subtests_filter)

        if not os.path.isdir(reference):  # Single file
            return self._make_tests(reference, which_tests, subtests_filter)

        tests = []

        def add_test_from_exception(exception):
            """ If the exc.filename is valid test it's added to tests """
            tests.extend(self._make_tests(exception.filename, which_tests))

        def skip_non_test(exception):
            """ Always return None """
            return None

        if which_tests is ALL:
            onerror = add_test_from_exception
        else:  # DEFAULT, AVAILABLE => skip missing tests
            onerror = skip_non_test

        for dirpath, dirs, filenames in os.walk(reference, onerror=onerror):
            dirs.sort()
            for file_name in sorted(filenames):
                if not file_name.startswith('.'):
                    for suffix in ignore_suffix:
                        if file_name.endswith(suffix):
                            break
                    else:
                        pth = os.path.join(dirpath, file_name)
                        tests.extend(self._make_tests(pth, which_tests))
        return tests

    def _find_avocado_tests(self, path, class_name=None):
        """
        Attempts to find Avocado instrumented tests from Python source files

        :param path: path to a Python source code file
        :type path: str
        :param class_name: the specific class to be found
        :type path: str
        :returns: dict with class name and additional info such as method names
                  and tags
        :rtype: dict
        """
        # If only the Test class was imported from the avocado namespace
        test_import = False
        # The name used, in case of 'from avocado import Test as AvocadoTest'
        test_import_name = None
        # If the "avocado" module itself was imported
        mod_import = False
        # The name used, in case of 'import avocado as avocadolib'
        mod_import_name = None
        # The resulting test classes
        result = {}

        if os.path.isdir(path):
            path = os.path.join(path, "__init__.py")

        mod = ast.parse(open(path).read(), path)

        for statement in mod.body:
            # Looking for a 'from avocado import Test'
            if (isinstance(statement, ast.ImportFrom) and
                    statement.module == 'avocado'):

                for name in statement.names:
                    if name.name == 'Test':
                        test_import = True
                        if name.asname is not None:
                            test_import_name = name.asname
                        else:
                            test_import_name = name.name
                        break

            # Looking for a 'import avocado'
            elif isinstance(statement, ast.Import):
                for name in statement.names:
                    if name.name == 'avocado':
                        mod_import = True
                        if name.asname is not None:
                            mod_import_name = name.nasname
                        else:
                            mod_import_name = name.name

            # Looking for a 'class Anything(anything):'
            elif isinstance(statement, ast.ClassDef):

                # class_name will exist only under recursion. In that
                # case, we will only process the class if it has the
                # expected class_name.
                if class_name is not None and class_name != statement.name:
                    continue

                docstring = ast.get_docstring(statement)
                # Looking for a class that has in the docstring either
                # ":avocado: enable" or ":avocado: disable
                has_disable = safeloader.check_docstring_directive(docstring,
                                                                   'disable')
                if (has_disable and class_name is None):
                    continue

                cl_tags = safeloader.get_docstring_directives_tags(docstring)

                has_enable = safeloader.check_docstring_directive(docstring,
                                                                  'enable')
                if (has_enable and class_name is None):
                    info = self._get_methods_info(statement.body, cl_tags)
                    result[statement.name] = info
                    continue

                # Looking for the 'recursive' docstring or a 'class_name'
                # (meaning we are under recursion)
                has_recurse = safeloader.check_docstring_directive(docstring,
                                                                   'recursive')
                if (has_recurse or class_name is not None):
                    info = self._get_methods_info(statement.body, cl_tags)
                    result[statement.name] = info

                    # Getting the list of parents of the current class
                    parents = statement.bases

                    # Searching the parents in the same module
                    for parent in parents[:]:
                        # Looking for a 'class FooTest(module.Parent)'
                        if isinstance(parent, ast.Attribute):
                            parent_class = parent.attr
                        # Looking for a 'class FooTest(Parent)'
                        else:
                            parent_class = parent.id

                        res = self._find_avocado_tests(path, parent_class)
                        if res:
                            parents.remove(parent)
                            for cls in res:
                                info.extend(res[cls])

                    # If there are parents left to be discovered, they
                    # might be in a different module.
                    for parent in parents:
                        if isinstance(parent, ast.Attribute):
                            # Looking for a 'class FooTest(module.Parent)'
                            parent_module = parent.value.id
                            parent_class = parent.attr
                        else:
                            # Looking for a 'class FooTest(Parent)'
                            parent_module = None
                            parent_class = parent.id

                        for node in mod.body:
                            reference = None
                            # Looking for 'from parent import class'
                            if isinstance(node, ast.ImportFrom):
                                reference = parent_class
                            # Looking for 'import parent'
                            elif isinstance(node, ast.Import):
                                reference = parent_module

                            if reference is None:
                                continue

                            for artifact in node.names:
                                # Looking for a class alias
                                # ('from parent import class as alias')
                                if artifact.asname is not None:
                                    parent_class = reference = artifact.name
                                # If the parent class or the parent module
                                # is found in the imports, discover the
                                # parent module path and find the parent
                                # class there
                                if artifact.name == reference:
                                    modules_paths = [os.path.dirname(path)]
                                    modules_paths.extend(sys.path)
                                    if parent_module is None:
                                        parent_module = node.module
                                    _, ppath, _ = imp.find_module(parent_module,
                                                                  modules_paths)
                                    res = self._find_avocado_tests(ppath,
                                                                   parent_class)
                                    if res:
                                        for cls in res:
                                            info.extend(res[cls])

                    continue

                if test_import:
                    base_ids = [base.id for base in statement.bases
                                if hasattr(base, 'id')]
                    # Looking for a 'class FooTest(Test):'
                    if test_import_name in base_ids:
                        info = self._get_methods_info(statement.body,
                                                      cl_tags)
                        result[statement.name] = info
                        continue

                # Looking for a 'class FooTest(avocado.Test):'
                if mod_import:
                    for base in statement.bases:
                        module = base.value.id
                        klass = base.attr
                        if module == mod_import_name and klass == 'Test':
                            info = self._get_methods_info(statement.body,
                                                          cl_tags)
                            result[statement.name] = info
                            continue

        return result

    @staticmethod
    def _get_methods_info(statement_body, class_tags):
        methods_info = []
        for st in statement_body:
            if (isinstance(st, ast.FunctionDef) and
                    st.name.startswith('test')):
                docstring = ast.get_docstring(st)
                mt_tags = safeloader.get_docstring_directives_tags(docstring)
                mt_tags.update(class_tags)

                methods = [method for method, tags in methods_info]
                if st.name not in methods:
                    methods_info.append((st.name, mt_tags))

        return methods_info

    def _make_avocado_tests(self, test_path, make_broken, subtests_filter,
                            test_name=None):
        if test_name is None:
            test_name = test_path
        try:
            tests = self._find_avocado_tests(test_path)
            if tests:
                test_factories = []
                for test_class, info in tests.items():
                    if isinstance(test_class, str):
                        for test_method, tags in info:
                            name = test_name + \
                                ':%s.%s' % (test_class, test_method)
                            if (subtests_filter and
                                    not subtests_filter.search(name)):
                                continue
                            tst = (test_class, {'name': name,
                                                'modulePath': test_path,
                                                'methodName': test_method,
                                                'tags': tags})
                            test_factories.append(tst)
                return test_factories
            else:
                if os.access(test_path, os.X_OK):
                    # Module does not have an avocado test class inside but
                    # it's executable, let's execute it.
                    return self._make_test(test.SimpleTest, test_path)
                else:
                    # Module does not have an avocado test class inside, and
                    # it's not executable. Not a Test.
                    return make_broken(NotATest, test_path,
                                       self.__not_test_str)

        # Since a lot of things can happen here, the broad exception is
        # justified. The user will get it unadulterated anyway, and avocado
        # will not crash.
        except BaseException as details:  # Ugly python files can raise any exc
            if isinstance(details, KeyboardInterrupt):
                raise  # Don't ignore ctrl+c
            if os.access(test_path, os.X_OK):
                # Module can't be imported, and it's executable. Let's try to
                # execute it.
                return self._make_test(test.SimpleTest, test_path)
            else:
                return make_broken(NotATest, test_path, self.__not_test_str)

    @staticmethod
    def _make_test(klass, uid, description=None):
        """
        Create test template
        :param klass: test class
        :param uid: test uid (by default used as id and name)
        :param description: Description appended to "uid" (for listing purpose)
        """
        if description:
            uid = "%s: %s" % (uid, description)
        return [(klass, {'name': uid})]

    def _make_tests(self, test_path, list_non_tests, subtests_filter=None):
        """
        Create test templates from given path
        :param test_path: File system path
        :param list_non_tests: include bad tests (NotATest, BrokenSymlink,...)
        :param subtests_filter: optional filter of methods for avocado tests
        """
        def ignore_broken(klass, uid, description=None):
            """ Always return empty list """
            return []

        if list_non_tests:  # return broken test with params
            make_broken = self._make_test
        else:  # return empty set instead
            make_broken = ignore_broken
        test_name = test_path
        if os.path.exists(test_path):
            if os.access(test_path, os.R_OK) is False:
                return make_broken(AccessDeniedPath, test_path, "Is not "
                                   "readable")
            path_analyzer = path.PathInspector(test_path)
            if path_analyzer.is_python():
                return self._make_avocado_tests(test_path, make_broken,
                                                subtests_filter)
            else:
                if os.access(test_path, os.X_OK):
                    return self._make_test(test.SimpleTest,
                                           test_path)
                else:
                    return make_broken(NotATest, test_path,
                                       self.__not_test_str)
        else:
            if os.path.islink(test_path):
                try:
                    if not os.path.isfile(os.readlink(test_path)):
                        return make_broken(BrokenSymlink, test_path, "Is a "
                                           "broken symlink")
                except OSError:
                    return make_broken(AccessDeniedPath, test_path, "Is not "
                                       "accessible.")

            # Try to resolve test ID (keep compatibility)
            test_path = os.path.join(data_dir.get_test_dir(), test_name)
            if os.path.exists(test_path):
                return self._make_avocado_tests(test_path, make_broken,
                                                subtests_filter, test_name)
            else:
                if not subtests_filter and ':' in test_name:
                    test_name, subtests_filter = test_name.split(':', 1)
                    test_path = os.path.join(data_dir.get_test_dir(),
                                             test_name)
                    if os.path.exists(test_path):
                        subtests_filter = re.compile(subtests_filter)
                        return self._make_avocado_tests(test_path, make_broken,
                                                        subtests_filter,
                                                        test_name)
                return make_broken(NotATest, test_name, "File not found "
                                   "('%s'; '%s')" % (test_name, test_path))
        return make_broken(NotATest, test_name, self.__not_test_str)


class ExternalLoader(TestLoader):

    """
    External-runner loader class
    """
    name = 'external'

    def __init__(self, args, extra_params):
        loader_options = extra_params.pop('loader_options', None)
        super(ExternalLoader, self).__init__(args, extra_params)
        if loader_options == '?':
            raise LoaderError("File loader accepts an option to set the "
                              "external-runner executable.")
        self._external_runner = self._process_external_runner(
            args, loader_options)

    @staticmethod
    def _process_external_runner(args, runner):
        """ Enables the external_runner when asked for """
        chdir = getattr(args, 'external_runner_chdir', None)
        test_dir = getattr(args, 'external_runner_testdir', None)

        if runner:
            external_runner_and_args = shlex.split(runner)
            executable = external_runner_and_args[0]
            if not os.path.exists(executable):
                msg = ('Could not find the external runner executable "%s"'
                       % executable)
                raise LoaderError(msg)
            if chdir == 'test':
                if not test_dir:
                    msg = ('Option "--external-runner-chdir=test" requires '
                           '"--external-runner-testdir" to be set.')
                    raise LoaderError(msg)
            elif test_dir:
                msg = ('Option "--external-runner-testdir" requires '
                       '"--external-runner-chdir=test".')
                raise LoaderError(msg)

            cls_external_runner = collections.namedtuple('ExternalLoader',
                                                         ['runner', 'chdir',
                                                          'test_dir'])
            return cls_external_runner(runner, chdir, test_dir)
        elif chdir:
            msg = ('Option "--external-runner-chdir" requires '
                   '"--external-runner" to be set.')
            raise LoaderError(msg)
        elif test_dir:
            msg = ('Option "--external-runner-testdir" requires '
                   '"--external-runner" to be set.')
            raise LoaderError(msg)
        return None  # Skip external runner

    def discover(self, reference, which_tests=DEFAULT):
        """
        :param reference: arguments passed to the external_runner
        :param which_tests: Limit tests to be displayed (ALL, AVAILABLE or
                            DEFAULT)
        :return: list of matching tests
        """
        if (not self._external_runner) or (reference is None):
            return []
        return [(test.ExternalRunnerTest, {'name': reference, 'external_runner':
                                           self._external_runner})]

    @staticmethod
    def get_type_label_mapping():
        return {test.ExternalRunnerTest: 'EXTERNAL'}

    @staticmethod
    def get_decorator_mapping():
        return {test.ExternalRunnerTest: output.TERM_SUPPORT.healthy_str}


class DummyLoader(TestLoader):

    """
    Dummy-runner loader class
    """
    name = 'dummy'

    def __init__(self, args, extra_params):
        super(DummyLoader, self).__init__(args, extra_params)

    def discover(self, url, which_tests=DEFAULT):
        return [(test.MockingTest, {'name': url})]

    @staticmethod
    def get_type_label_mapping():
        return {test.MockingTest: 'DUMMY'}

    @staticmethod
    def get_decorator_mapping():
        return {test.MockingTest: output.TERM_SUPPORT.healthy_str}


loader = TestLoaderProxy()
