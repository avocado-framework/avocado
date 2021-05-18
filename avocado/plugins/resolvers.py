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
# Copyright: Red Hat Inc. 2019
# Authors: Cleber Rosa <crosa@redhat.com>

"""
Test resolver for builtin test types
"""

import os
import re

from avocado.core.nrunner import Runnable
from avocado.core.plugin_interfaces import Discoverer, Resolver
from avocado.core.references import reference_split
from avocado.core.resolver import (ReferenceResolution,
                                   ReferenceResolutionResult, check_file,
                                   extend_directory)
from avocado.core.safeloader import find_avocado_tests, find_python_unittests
from avocado.core.settings import settings


def discover(resolver):
    resolutions = []
    config = settings.as_dict()
    if config.get('list.resolver'):
        for reference in extend_directory(config.get("datadir.paths.test_dir")):
            if not os.path.exists(reference):
                resolutions.append(resolver.resolve(reference))
    return resolutions


class ExecTestResolver(Resolver):

    name = 'exec-test'
    description = 'Test resolver for executable files to be handled as tests'

    @staticmethod
    def resolve(reference):

        criteria_check = check_file(reference, reference, suffix=None,
                                    type_name='executable file',
                                    access_check=os.R_OK | os.X_OK,
                                    access_name='executable')
        if criteria_check is not True:
            return criteria_check

        return ReferenceResolution(reference,
                                   ReferenceResolutionResult.SUCCESS,
                                   [Runnable('exec-test', reference,
                                             config=settings.as_dict(r'^runner\.'))])


class ExecTestDiscoverer(Discoverer):

    name = 'exec-test-discoverer'
    description = 'Test discoverer for executable files to be handled as tests'

    @staticmethod
    def discover():
        return discover(ExecTestResolver)


def python_resolver(name, reference, find_tests):
    module_path, tests_filter = reference_split(reference)
    if tests_filter is not None:
        tests_filter = re.compile(tests_filter)

    criteria_check = check_file(module_path, reference)
    if criteria_check is not True:
        return criteria_check

    # disabled tests not needed here
    class_methods_info, _ = find_tests(module_path)
    runnables = []
    for klass, methods_tags_reqs in class_methods_info.items():
        for (method, tags, reqs) in methods_tags_reqs:
            klass_method = "%s.%s" % (klass, method)
            if tests_filter is not None and not tests_filter.search(klass_method):
                continue
            uri = "%s:%s" % (module_path, klass_method)
            runnables.append(Runnable(name,
                                      uri=uri,
                                      tags=tags,
                                      requirements=reqs,
                                      config=settings.as_dict(r'^runner\.')))
    if runnables:
        return ReferenceResolution(reference,
                                   ReferenceResolutionResult.SUCCESS,
                                   runnables)

    return ReferenceResolution(reference,
                               ReferenceResolutionResult.NOTFOUND)


class PythonUnittestResolver(Resolver):

    name = 'python-unittest'
    description = 'Test resolver for Python Unittests'

    @staticmethod
    def _find_compat(module_path):
        """Used as compatibility for the :func:`python_resolver()` interface."""
        return find_python_unittests(module_path), None

    @staticmethod
    def resolve(reference):
        return python_resolver(PythonUnittestResolver.name,
                               reference,
                               PythonUnittestResolver._find_compat)


class PythonUnittestDiscoverer(Discoverer):

    name = 'python-unittest-discoverer'
    description = 'Test discoverer for Python Unittests'

    @staticmethod
    def discover():
        return discover(PythonUnittestResolver)


class AvocadoInstrumentedResolver(Resolver):

    name = 'avocado-instrumented'
    description = 'Test resolver for Avocado Instrumented tests'

    @staticmethod
    def resolve(reference):
        return python_resolver(AvocadoInstrumentedResolver.name,
                               reference,
                               find_avocado_tests)


class AvocadoInstrumentedDiscoverer(Discoverer):
    name = 'avocado-instrumented-discoverer'
    description = 'Test discoverer for Avocado Instrumented tests'

    @staticmethod
    def discover():
        return discover(AvocadoInstrumentedResolver)


class TapResolver(Resolver):

    name = 'tap'
    description = 'Test resolver for executable files to be handled as tests'

    @staticmethod
    def resolve(reference):

        criteria_check = check_file(reference, reference, suffix=None,
                                    type_name='executable file',
                                    access_check=os.R_OK | os.X_OK,
                                    access_name='executable')
        if criteria_check is not True:
            return criteria_check

        return ReferenceResolution(reference,
                                   ReferenceResolutionResult.SUCCESS,
                                   [Runnable('tap', reference,
                                             config=settings.as_dict(r'^runner\.'))])


class TapResolverDiscoverer(Discoverer):
    name = 'tap-discoverer'
    description = 'Test discoverer for executable files to be handled as tests'

    @staticmethod
    def discover():
        return discover(TapResolver)
