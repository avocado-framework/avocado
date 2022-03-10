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
# Copyright: Red Hat Inc. 2022
# Authors: Jan Richter <jarichte@redhat.com>

from avocado.core.nrunner.runnable import Runnable


def pre_test_runnables(test_runnable, kind):
    runnables = []
    if test_runnable.dependencies:
        for dependency in test_runnable.dependencies:
            if dependency['type'] == kind:
                # make a copy to change the dictionary and do not affect
                # the original `dependencies` dictionary from the test
                dependency_copy = dependency.copy()
                kind = dependency_copy.pop('type')
                runnable = Runnable(kind, None,
                                    config=test_runnable.config,
                                    **dependency_copy)
                runnables.append(runnable)
    return runnables
