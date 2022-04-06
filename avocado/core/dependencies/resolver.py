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


class DependencyResolver:

    name = 'dependency'
    description = 'Dependency resolver for tests with dependencies'

    @staticmethod
    def resolve(runnable):
        dependency_runnables = []
        for dependency in runnable.dependencies:
            # make a copy to change the dictionary and do not affect the
            # original `dependencies` dictionary from the test
            dependency_copy = dependency.copy()
            kind = dependency_copy.pop('type')
            dependency_runnable = Runnable(kind, None, config=runnable.config,
                                           **dependency_copy)
            dependency_runnables.append(dependency_runnable)
        return dependency_runnables
