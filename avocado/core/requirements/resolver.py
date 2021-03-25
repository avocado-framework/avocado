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

from ..nrunner import Runnable


class RequirementsResolver:

    name = 'requirements'
    description = 'Requirements resolver for tests with requirements'

    @staticmethod
    def resolve(runnable):
        requirements_runnables = []
        for requirement in runnable.requirements:
            # make a copy to change the dictionary and do not affect the
            # original `requirements` dictionary from the test
            requirement_copy = requirement.copy()
            kind = 'requirement-%s' % requirement_copy.pop('type')
            requirement_runnable = Runnable(kind, None, **requirement_copy)
            requirements_runnables.append(requirement_runnable)
        return requirements_runnables
