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
Test resolver for executable files
"""

import os

from avocado.core.plugin_interfaces import Resolver
from avocado.core.resolver import ReferenceResolution
from avocado.core.resolver import ReferenceResolutionResult
from avocado.core.nrunner import Runnable


class ExecTestResolver(Resolver):

    name = 'exec-test'
    description = 'Test resolver for executable files to be handled as tests'

    @staticmethod
    def resolve(reference):
        if os.path.isfile(reference) and os.access(reference, os.X_OK):
            return ReferenceResolution(reference,
                                       ReferenceResolutionResult.SUCCESS,
                                       [Runnable('exec-test', reference)])
        else:
            return ReferenceResolution(reference,
                                       ReferenceResolutionResult.NOTFOUND)
