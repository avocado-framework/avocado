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
from avocado.core.safeloader import find_python_unittests
from avocado.core.resolver import ReferenceResolution
from avocado.core.resolver import ReferenceResolutionResult
from avocado.core.nrunner import Runnable


class PythonUnittestResolver(Resolver):

    name = 'python-unittest'
    description = 'Test resolver for Python Unittests'

    @staticmethod
    def resolve(reference):
        if os.path.isfile(reference) and os.access(reference, os.R_OK):
            class_methods = find_python_unittests(reference)
            if class_methods:
                runnables = []
                mod = os.path.relpath(reference)
                if mod.endswith('.py'):
                    mod = mod[:-3]
                mod = mod.replace(os.path.sep, ".")
                for klass, meths in class_methods.items():
                    for (meth, _) in meths:
                        runnables.append(Runnable('python-unittest',
                                                  '%s.%s.%s' % (mod, klass, meth)))
            return ReferenceResolution(reference,
                                       ReferenceResolutionResult.SUCCESS,
                                       runnables)
        else:
            return ReferenceResolution(reference,
                                       ReferenceResolutionResult.NOTFOUND)
