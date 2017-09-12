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
Test resolver for Avocado Instrumented tests
"""

import os

from avocado.core.plugin_interfaces import Resolver
from avocado.core.safeloader import find_avocado_tests
from avocado.core.resolver import ReferenceResolution
from avocado.core.resolver import ReferenceResolutionResult
from avocado.core.nrunner import Runnable


class AvocadoInstrumentedResolver(Resolver):

    name = 'avocado-instrumented'
    description = 'Test resolver for Avocado Instrumented tests'

    @staticmethod
    def resolve(reference):
        if ':' in reference:
            module_path, _ = reference.split(':', 1)
        else:
            module_path = reference
        if os.path.isfile(module_path) and os.access(module_path, os.R_OK):
            # disabled tests not needed here
            class_methods_info, _ = find_avocado_tests(module_path)
            runnables = []
            for klass, methods_tags in class_methods_info.items():
                for (method, _) in methods_tags:
                    uri = "%s:%s.%s" % (module_path, klass, method)
                    runnables.append(Runnable('avocado-instrumented', uri))
            if runnables:
                return ReferenceResolution(reference,
                                           ReferenceResolutionResult.SUCCESS,
                                           runnables)
        return ReferenceResolution(reference,
                                   ReferenceResolutionResult.NOTFOUND)
