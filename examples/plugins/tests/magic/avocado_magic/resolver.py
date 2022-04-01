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
# Copyright: Red Hat Inc. 2020
# Authors: Cleber Rosa <crosa@redhat.com>

"""
Test resolver for magic test words
"""

from avocado.core.nrunner.runnable import Runnable
from avocado.core.plugin_interfaces import Discoverer, Resolver
from avocado.core.resolver import (ReferenceResolution,
                                   ReferenceResolutionResult)

VALID_MAGIC_WORDS = ['pass', 'fail']


class MagicResolver(Resolver):

    name = 'magic'
    description = 'Test resolver for magic words'

    @staticmethod
    def resolve(reference):
        if reference not in VALID_MAGIC_WORDS:
            return ReferenceResolution(
                reference,
                ReferenceResolutionResult.NOTFOUND,
                info=f'Word "{reference}" is not a valid magic word')

        return ReferenceResolution(reference,
                                   ReferenceResolutionResult.SUCCESS,
                                   [Runnable('magic', reference)])


class MagicDiscoverer(Discoverer):

    name = 'magic-discoverer'
    description = 'Test discoverer for magic words'

    @staticmethod
    def discover():
        resolutions = []
        for reference in VALID_MAGIC_WORDS:
            resolutions.append(MagicResolver.resolve(reference))
        return resolutions
