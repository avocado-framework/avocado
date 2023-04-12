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
# Copyright: Red Hat Inc. 2021
# Authors: Willian Rampazzo <willianr@redhat.com>

from avocado.core.nrunner.runnable import Runnable
from avocado.core.plugin_interfaces import PreTest


class DependencyResolver(PreTest):
    """Implements the dependency pre tests plugin.

    It will create pre-test tasks for managing dependencies based on the
    `:avocado: dependency=` definition inside the test’s docstring.

    """

    name = "dependency"
    description = "Dependency resolver for tests with dependencies"
    is_cacheable = True

    @staticmethod
    def pre_test_runnables(test_runnable, suite_config=None):  # pylint: disable=W0221
        if not test_runnable.dependencies:
            return []
        dependency_runnables = []
        for dependency in test_runnable.dependencies:
            # make a copy to change the dictionary and do not affect the
            # original `dependencies` dictionary from the test
            dependency_copy = dependency.copy()
            kind = dependency_copy.pop("type")
            uri = dependency_copy.pop("uri", None)
            args = dependency_copy.pop("args", ())
            dependency_runnable = Runnable(
                kind, uri, *args, config=test_runnable.config, **dependency_copy
            )
            dependency_runnables.append(dependency_runnable)
        return dependency_runnables
