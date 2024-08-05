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
        unique_dependencies = list(dict.fromkeys(test_runnable.dependencies))
        for dependency in unique_dependencies:
            dependency_runnables.append(dependency.to_runnable(test_runnable.config))
        return dependency_runnables
