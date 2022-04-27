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
import re
import sys
from enum import Enum

from avocado.core import data_dir, output, safeloader, test
from avocado.core.output import LOG_UI
from avocado.core.references import reference_split
from avocado.core.settings import settings
from avocado.utils import stacktrace


class DiscoverMode(Enum):
    #: Show default tests (for execution)
    DEFAULT = object()
    #: Available tests (for listing purposes)
    AVAILABLE = object()
    #: All tests (including broken ones)
    ALL = object()


class MissingTest:
    """
    Class representing reference which failed to be discovered
    """


class BrokenSymlink:
    """ Dummy object to represent reference pointing to a BrokenSymlink path """


class AccessDeniedPath:
    """ Dummy object to represent reference pointing to a inaccessible path """


class NotATest:
    """
    Class representing something that is not a test
    """


class LoaderError(Exception):
    """ Loader exception """


class InvalidLoaderPlugin(LoaderError):
    """ Invalid loader plugin """


class LoaderUnhandledReferenceError(LoaderError):

    """ Test References not handled by any resolver """

    def __init__(self, unhandled_references, plugins):
        super().__init__()
        self.unhandled_references = unhandled_references
        self.plugins = [_.name for _ in plugins]

    def __str__(self):
        ref1 = "', '" .join(self.unhandled_references)
        plugins = "', '".join(self.plugins)
        ref2 = " ".join(self.unhandled_references)
        return (f"Unable to resolve reference(s) '{ref1}' "
                f"with plugins(s) '{plugins}', try running "
                f"'avocado -V list {ref2}' to see the details.")


class TestLoaderProxy:

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
            raise InvalidLoaderPlugin(f"Object {plugin} is not an instance "
                                      f"of TestLoader")

    def load_plugins(self, config):
        if self._initialized_plugins:
            return

        def _good_test_types(plugin):
            """
            List all supported test types (excluding incorrect ones)
            """
            name = plugin.name
            mapping = plugin.get_type_label_mapping()
            # Using __func__ to avoid problem with different term_supp instances
            healthy_func = getattr(output.TERM_SUPPORT.healthy_str, '__func__')
            types = [mapping[_[0]]
                     for _ in plugin.get_decorator_mapping().items()
                     if _[1].__func__ is healthy_func]
            return [name + '.' + _ for _ in types]

        def _str_loaders():
            """
            :return: string of sorted loaders and types
            """
            out = ""
            for plugin in self.registered_plugins:
                out += (f"  {plugin.name}: "
                        f"{', '.join(_good_test_types(plugin))}\n")
            return out.rstrip('\n')

        # When running from the JobAPI there is no subcommand
        subcommand = config.get('subcommand') or 'run'
        # Add (default) file loader if not already registered
        if FileLoader not in self.registered_plugins:
            self.register_plugin(FileLoader)
        supported_loaders = [_.name for _ in self.registered_plugins]
        supported_types = []
        for plugin in self.registered_plugins:
            supported_types.extend(_good_test_types(plugin))

        # Here is one of the few exceptions that has a hardcoded default
        loaders = config.get(f"{subcommand}.loaders") or ['file', '@DEFAULT']
        if "@DEFAULT" in loaders:  # Replace @DEFAULT with unused loaders
            idx = loaders.index("@DEFAULT")
            loaders = (loaders[:idx] + [plugin for plugin in supported_loaders
                                        if plugin not in loaders] +
                       loaders[idx + 1:])
            # Remove duplicate @DEFAULT entries
            loaders = [item for item in loaders if item != "@DEFAULT"]

        loaders = [_.split(':', 1) for _ in loaders]
        priority = [_[0] for _ in loaders]
        for i, name in enumerate(priority):
            extra_params = {}
            if name in supported_types:
                name, extra_params['allowed_test_types'] = name.split('.', 1)
            elif name not in supported_loaders:
                raise InvalidLoaderPlugin(f"Unknown loader '{name}'. "
                                          f"Available plugins are:\n"
                                          f"{ _str_loaders()}")
            if len(loaders[i]) == 2:
                extra_params['loader_options'] = loaders[i][1]
            plugin = self.registered_plugins[supported_loaders.index(name)]
            self._initialized_plugins.append(plugin(config, extra_params))

    def _update_mappings(self):
        """
        Update the mappings according the current initialized plugins
        """
        # Plugins are initialized, let's update mappings
        self._label_mapping = {MissingTest: "MISSING"}
        for plugin in self._initialized_plugins:
            self._label_mapping.update(plugin.get_full_type_label_mapping())
        self._decorator_mapping = {MissingTest:
                                   output.TERM_SUPPORT.fail_header_str}
        for plugin in self._initialized_plugins:
            self._decorator_mapping.update(plugin.get_full_decorator_mapping())

    def get_extra_listing(self):
        for loader_plugin in self._initialized_plugins:
            loader_plugin.get_extra_listing()

    def get_base_keywords(self):
        base_path = []
        for loader_plugin in self._initialized_plugins:
            base_path += loader_plugin.get_base_keywords()
        return base_path

    def get_type_label_mapping(self):
        if self._label_mapping is None:
            raise RuntimeError("LoaderProxy.discover has to be called before "
                               "LoaderProxy.get_type_label_mapping")
        return self._label_mapping

    def get_decorator_mapping(self):
        if self._label_mapping is None:
            raise RuntimeError("LoaderProxy.discover has to be called before "
                               "LoaderProxy.get_decorator_mapping")
        return self._decorator_mapping

    def discover(self, references, which_tests=DiscoverMode.DEFAULT, force=None):
        """
        Discover (possible) tests from test references.

        :param references: a list of tests references; if [] use plugin defaults
        :type references: builtin.list
        :param which_tests: Limit tests to be displayed
        :type which_tests: :class:`DiscoverMode`
        :param force: don't raise an exception when some test references
                      are not resolved to tests.
        :return: A list of test factories (tuples (TestClass, test_params))
        """
        def handle_exception(plugin, details):
            # FIXME: Introduce avocado.exceptions logger and use here
            stacktrace.log_message((f"Test discovery plugin {plugin} "
                                    f"failed: {details}"),
                                   LOG_UI.getChild("exceptions"))
            # FIXME: Introduce avocado.traceback logger and use here
            stacktrace.log_exc_info(sys.exc_info(), LOG_UI.getChild("debug"))
        tests = []
        unhandled_references = []
        if not references:
            for loader_plugin in self._initialized_plugins:
                try:
                    tests.extend(loader_plugin.discover(None, which_tests))
                except Exception as details:  # pylint: disable=W0703
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
                            if which_tests != DiscoverMode.ALL:
                                break  # Don't process other plugins
                    except Exception as details:  # pylint: disable=W0703
                        handle_exception(loader_plugin, details)
                if not handled:
                    unhandled_references.append(reference)
        if unhandled_references:
            if which_tests == DiscoverMode.ALL:
                tests.extend([(MissingTest, {'name': reference})
                              for reference in unhandled_references])
            else:
                # This is a workaround to avoid changing the method signature
                if force is True or force == 'on':
                    LOG_UI.error(LoaderUnhandledReferenceError(unhandled_references,
                                                               self._initialized_plugins))
                else:
                    raise LoaderUnhandledReferenceError(unhandled_references,
                                                        self._initialized_plugins)
        self._update_mappings()
        return tests

    def clear_plugins(self):
        self.registered_plugins = []


class TestLoader:

    """
    Base for test loader classes
    """

    name = None     # Human friendly name of the loader

    def __init__(self, config, extra_params):  # pylint: disable=W0613
        if "allowed_test_types" in extra_params:
            mapping = self.get_type_label_mapping()
            types = extra_params.pop("allowed_test_types")
            if len(mapping) != 1:
                msg = (f"Loader '{self.name}' supports multiple test types "
                       f"but does not handle the 'allowed_test_types'. "
                       f"Either don't use '{self.name}' instead of "
                       f"'{self.name}.{types}' or take care of the "
                       f"'allowed_test_types' in the plugin.")
                raise LoaderError(msg)
            elif next(iter(mapping.values())) != types:
                raise LoaderError(f"Loader '{self.name}' doesn't support "
                                  f"test type '{types}', it supports only "
                                  f"'{next(iter(mapping.values()))}'")
        if "loader_options" in extra_params:
            raise LoaderError(f"Loader '{self.name}' doesn't support "
                              f"'loader_options', please don't use "
                              f"--loader {self.name}:"
                              f"{extra_params.get('loader_options')}")
        if extra_params:
            raise LoaderError(f"Loader '{self.name}' doesn't handle extra "
                              f"params {extra_params}, please adjust your "
                              f"plugin to take care of them.")
        self.config = config

    def get_extra_listing(self):
        pass

    @staticmethod
    def get_type_label_mapping():
        """
        Get label mapping for display in test listing.

        :return: Dict {TestClass: 'TEST_LABEL_STRING'}
        """
        raise NotImplementedError

    def get_full_type_label_mapping(self):     # pylint: disable=R0201
        """
        Allows extending the type-label-mapping after the object is initialized
        """
        return self.get_type_label_mapping()

    @staticmethod
    def get_decorator_mapping():
        """
        Get label mapping for display in test listing.

        :return: Dict {TestClass: decorator function}
        """
        raise NotImplementedError

    def get_full_decorator_mapping(self):      # pylint: disable=R0201
        """
        Allows extending the decorator-mapping after the object is initialized
        """
        return self.get_decorator_mapping()

    def discover(self, reference, which_tests=DiscoverMode.DEFAULT):
        """
        Discover (possible) tests from an reference.

        :param reference: the reference to be inspected.
        :type reference: str
        :param which_tests: Limit tests to be displayed
        :type which_tests: :class:`DiscoverMode`
        :return: a list of test matching the reference as params.
        """
        raise NotImplementedError


def add_loader_options(parser, section='run'):
    arggrp = parser.add_argument_group('loader options')
    help_msg = ("Overrides the priority of the test loaders. You can specify "
                "either @loader_name or TEST_TYPE. By default it tries all "
                "available loaders according to priority set in "
                "settings->plugins.loaders.")
    settings.register_option(section=section,
                             key='loaders',
                             nargs='+',
                             key_type=list,
                             default=['file', '@DEFAULT'],
                             help_msg=help_msg,
                             parser=arggrp,
                             long_arg='--loaders',
                             metavar='LOADER_NAME_OR_TEST_TYPE')


class FileLoader(TestLoader):

    """
    Test loader class.
    """

    name = 'file'
    NOT_TEST_STR = "Not an INSTRUMENTED (avocado.Test based) test"

    def __init__(self, config, extra_params):
        test_type = extra_params.pop('allowed_test_types', None)
        super().__init__(config, extra_params)
        self.test_type = test_type

    @staticmethod
    def get_type_label_mapping():
        return {NotATest: 'NOT_A_TEST',
                BrokenSymlink: 'BROKEN_SYMLINK',
                AccessDeniedPath: 'ACCESS_DENIED',
                test.Test: 'INSTRUMENTED'}

    @staticmethod
    def get_decorator_mapping():
        return {NotATest: output.TERM_SUPPORT.warn_header_str,
                BrokenSymlink: output.TERM_SUPPORT.fail_header_str,
                AccessDeniedPath: output.TERM_SUPPORT.fail_header_str,
                test.Test: output.TERM_SUPPORT.healthy_str}

    @staticmethod
    def _is_matching_test_class(tst, test_class):
        if test_class is test.Test:
            # Instrumented tests are defined as string and loaded at the
            # execution time.
            return isinstance(tst, str)
        else:
            return not isinstance(tst, str) and issubclass(tst, test_class)

    def discover(self, reference, which_tests=DiscoverMode.DEFAULT):
        """
        Discover (possible) tests from a directory.

        Recursively walk in a directory and find tests params.
        The tests are returned in alphabetic order.

        Afterwards when "allowed_test_types" is supplied it verifies if all
        found tests are of the allowed type. If not return None (even on
        partial match).

        :param reference: the directory path to inspect.
        :param which_tests: Limit tests to be displayed
        :type which_tests: :class:`DiscoverMode`
        :return: list of matching tests
        """
        tests = self._discover(reference, which_tests)
        if self.test_type:
            mapping = self.get_type_label_mapping()
            test_class = next(key for key, value in mapping.items()
                              if value == self.test_type)
            for tst in tests:
                if not self._is_matching_test_class(tst[0], test_class):
                    return None
        return tests

    def _discover(self, reference, which_tests=DiscoverMode.DEFAULT):
        """
        Recursively walk in a directory and find tests params.
        The tests are returned in alphabetic order.

        :param reference: the directory path to inspect.
        :param which_tests: Limit tests to be displayed
        :type which_tests: :class:`DiscoverMode`
        :return: list of matching tests
        """
        if reference is None:
            if which_tests == DiscoverMode.DEFAULT:
                return []  # Return empty set when not listing details
            else:
                reference = data_dir.get_test_dir()
        ignore_suffix = ('.data', '.pyc', '.pyo', '__init__.py',
                         '__main__.py')

        # Look for filename:test_method pattern
        reference, subtests_filter = reference_split(reference)
        if subtests_filter is not None:
            subtests_filter = re.compile(subtests_filter)

        if not os.path.isdir(reference):  # Single file
            return self._make_tests(reference, which_tests == DiscoverMode.ALL,
                                    subtests_filter)

        tests = []

        def add_test_from_exception(exception):
            """ If the exc.filename is valid test it's added to tests """
            tests.extend(self._make_tests(exception.filename,
                                          which_tests == DiscoverMode.ALL))

        def skip_non_test(exception):  # pylint: disable=W0613
            """ Always return None """
            return None

        if which_tests == DiscoverMode.ALL:
            onerror = add_test_from_exception
        else:  # DEFAULT, AVAILABLE => skip missing tests
            onerror = skip_non_test

        for dirpath, dirs, filenames in os.walk(reference, onerror=onerror):
            dirs.sort()
            for file_name in sorted(filenames):
                if file_name.startswith('.') or file_name.endswith(ignore_suffix):
                    continue

                pth = os.path.join(dirpath, file_name)
                tests.extend(self._make_tests(pth,
                                              which_tests == DiscoverMode.ALL,
                                              subtests_filter))
        return tests

    def _make_existing_file_tests(self, test_path, make_broken,
                                  subtests_filter):
        if test_path.endswith('.py'):
            return self._make_python_file_tests(test_path, make_broken,
                                                subtests_filter)
        else:
            return make_broken(NotATest, test_path,
                               self.NOT_TEST_STR)

    def _make_nonexisting_file_tests(self, test_path, make_broken,
                                     subtests_filter, test_name):
        # Try to resolve test ID (keep compatibility)
        test_path = os.path.join(data_dir.get_test_dir(), test_name)
        if os.path.exists(test_path):
            return self._make_python_file_tests(test_path, make_broken,
                                                subtests_filter,
                                                test_name)
        else:
            if not subtests_filter and ':' in test_name:
                test_name, subtests_filter = test_name.split(':', 1)
                test_path = os.path.join(data_dir.get_test_dir(),
                                         test_name)
                if os.path.exists(test_path):
                    subtests_filter = re.compile(subtests_filter)
                    return self._make_python_file_tests(test_path,
                                                        make_broken,
                                                        subtests_filter,
                                                        test_name)
            return make_broken(NotATest, test_name,
                               (f"File not found ('{test_name}'; "
                                f"'{test_path}')"))

    @staticmethod
    def _make_test(klass, uid, description=None, subtests_filter=None,
                   **test_arguments):
        """
        Create test template
        :param klass: test class
        :param uid: test uid (by default used as id and name)
        :param description: Description appended to "uid" (for listing purpose)
        :param subtests_filter: optional filter of methods for avocado tests
        :param test_arguments: arguments to be passed to the klass(test_arguments)
        """
        if subtests_filter and not subtests_filter.search(uid):
            return []

        if description:
            uid = f"{uid}: {description}"
        test_arguments["name"] = uid
        return [(klass, test_arguments)]

    def _make_tests(self, test_path, list_non_tests, subtests_filter=None):
        """
        Create test templates from given path
        :param test_path: File system path
        :param list_non_tests: include bad tests (NotATest, BrokenSymlink,...)
        :param subtests_filter: optional filter of methods for avocado tests
        """
        def ignore_broken(klass, uid, description=None):  # pylint: disable=W0613
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
            return self._make_existing_file_tests(test_path, make_broken,
                                                  subtests_filter)
        else:
            if os.path.islink(test_path):
                try:
                    if not os.path.isfile(os.readlink(test_path)):
                        return make_broken(BrokenSymlink, test_path, "Is a "
                                           "broken symlink")
                except OSError:
                    return make_broken(AccessDeniedPath, test_path, "Is not "
                                       "accessible.")
            return self._make_nonexisting_file_tests(test_path, make_broken,
                                                     subtests_filter,
                                                     test_name)

    def _make_python_file_tests(self, test_path, make_broken,
                                subtests_filter, test_name=None):
        if test_name is None:
            test_name = test_path
        try:
            # Avocado tests
            avocado_tests, _ = safeloader.find_avocado_tests(test_path)
            if avocado_tests:
                test_factories = []
                for test_class, info in avocado_tests.items():
                    if isinstance(test_class, str):
                        for test_method, tags, _ in info:
                            name = test_name + \
                                f':{test_class}.{test_method}'
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
                return make_broken(NotATest, test_path,
                                   self.NOT_TEST_STR)

        # Since a lot of things can happen here, the broad exception is
        # justified. The user will get it unadulterated anyway, and avocado
        # will not crash. Ugly python files can raise any exception
        except BaseException as details:  # pylint: disable=W0703
            if isinstance(details, KeyboardInterrupt):
                raise  # Don't ignore ctrl+c
            else:
                return make_broken(NotATest, test_path,
                                   self.NOT_TEST_STR)


loader = TestLoaderProxy()
