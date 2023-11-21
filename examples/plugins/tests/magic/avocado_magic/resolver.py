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
from avocado.core.plugin_interfaces import Discoverer, Init, Resolver
from avocado.core.resolver import ReferenceResolution, ReferenceResolutionResult
from avocado.core.settings import settings

VALID_MAGIC_WORDS = ["pass", "fail"]


class MagicResolver(Resolver):

    name = "magic"
    description = "Test resolver for magic words"

    @staticmethod
    def resolve(reference):  # pylint: disable=W0221
        try:
            key_word, magic_word = reference.split(":", 1)
        except (ValueError):
            key_word = None
            magic_word = reference
        if key_word != "magic":
            return ReferenceResolution(
                reference,
                ReferenceResolutionResult.NOTFOUND,
                info=f'Word "{reference}" is not a valid magic word',
            )

        if magic_word not in VALID_MAGIC_WORDS:
            return ReferenceResolution(
                reference,
                ReferenceResolutionResult.CORRUPT,
                [Runnable("magic", reference)],
                info=f'Word "{reference}" is magic type but the {magic_word} is not a valid magic word',
            )

        return ReferenceResolution(
            reference, ReferenceResolutionResult.SUCCESS, [Runnable("magic", reference)]
        )


class MagicInit(Init):

    description = "Initialization for magic words plugin"

    def initialize(self):
        settings.register_option(
            section="examples.plugins.magic.discover",
            key="enabled",
            key_type=bool,
            help_msg="Whether to enable the discovery of pass and fail",
            default=False,
        )


class MagicDiscoverer(Discoverer):

    name = "magic-discoverer"
    description = "Test discoverer for magic words"

    def discover(self):  # pylint: disable=W0221
        resolutions = []
        if self.config.get("examples.plugins.magic.discover.enabled"):
            for reference in VALID_MAGIC_WORDS:
                resolutions.append(MagicResolver.resolve(reference))
        return resolutions
