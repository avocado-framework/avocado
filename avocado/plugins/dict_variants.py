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

from avocado.core import varianter
from avocado.core.plugin_interfaces import Init, Varianter
from avocado.core.settings import settings
from avocado.core.tree import TreeNode


class DictVariantsInit(Init):

    name = 'dict_variants'
    description = "Python Dictionary based varianter"

    def initialize(self):
        help_msg = 'Load the Variants from Python dictionaries'
        settings.register_option(section='run',
                                 key='dict_variants',
                                 default=[],
                                 key_type=list,
                                 help_msg=help_msg)

        help_msg = ('Configure the key that will be used to name the '
                    'variant ID. If not set, will use all keys.')
        settings.register_option(section='run.dict_variants',
                                 key='variant_id_keys',
                                 default=[],
                                 key_type=list,
                                 help_msg=help_msg)


class DictVariants(Varianter):

    """
    Turns (a list of) Python dictionaries into variants
    """

    name = 'dict_variants'
    description = "Python Dictionary based varianter"

    def initialize(self, config):
        # pylint: disable=W0201
        self.variants = config.get('run.dict_variants')
        if self.variants:
            # pylint: disable=W0201
            self.headers = [key for key in self.variants[0].keys()]
            self.headers_for_id = config.get('run.dict_variants.variant_id_keys')
            if not self.headers_for_id:
                self.headers_for_id = self.headers

    def __iter__(self):
        if self.variants is None:
            return

        variant_ids = []
        for variant in self.variants:
            variant_ids.append("-".join([str(variant.get(key))
                                         for key in self.headers_for_id]))

        for vid, variant in zip(variant_ids, self.variants):
            yield {"variant_id": vid,
                   "variant": [TreeNode('', variant)],
                   "paths": ['/']}

    def __len__(self):
        return sum(1 for _ in self.variants) if self.variants else 0

    def to_str(self, summary, variants, **kwargs):
        """
        Return human readable representation

        The summary/variants accepts verbosity where 0 means silent and
        maximum is up to the plugin.

        :param summary: How verbose summary to output (int)
        :param variants: How verbose list of variants to output (int)
        :param kwargs: Other free-form arguments
        :rtype: str
        """
        if not self.variants:
            return ""
        out = []

        if variants:
            # variants == 0 means disable, but in plugin it's brief
            out.append("Dict Variants (%s):" % len(self))
            for variant in self:
                out.extend(varianter.variant_to_str(variant, variants - 1,
                                                    kwargs, False))
        return "\n".join(out)
