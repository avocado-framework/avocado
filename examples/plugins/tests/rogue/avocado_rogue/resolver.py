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
# Copyright: Red Hat Inc. 2023
# Authors: Cleber Rosa <crosa@redhat.com>

"""
Test resolver for the "rogue" magic word
"""

from avocado_rogue import MAGIC_WORD

from avocado.core.nrunner.runnable import Runnable
from avocado.core.plugin_interfaces import Resolver
from avocado.core.resolver import ReferenceResolution, ReferenceResolutionResult


class RogueResolver(Resolver):

    name = "rogue"
    description = "Test resolver for rogue magic word"

    @staticmethod
    def resolve(reference):  # pylint: disable=W0221
        if reference != MAGIC_WORD:
            return ReferenceResolution(
                reference,
                ReferenceResolutionResult.NOTFOUND,
                info=f'Word "{reference}" is not the magic word',
            )

        return ReferenceResolution(
            reference,
            ReferenceResolutionResult.SUCCESS,
            [Runnable("rogue", reference)],
        )
