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
# Copyright: Red Hat Inc. 2018
# Authors: Amador Pahim <apahim@redhat.com>

import json
import sys

from avocado.core import exit_codes
from avocado.core import varianter
from avocado.core.future.settings import settings
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLI
from avocado.core.plugin_interfaces import Varianter


_NO_VARIANTS = -1


class JsonVariantsCLI(CLI):

    """
    Serialized based Varianter options
    """

    name = 'json variants'
    description = "JSON serialized based Varianter options for the 'run' " \
                  "subcommand"

    def configure(self, parser):

        help_msg = 'Load the Variants from a JSON serialized file'
        for name in ("run", "variants"):  # intentionally omitting "multiplex"
            subparser = parser.subcommands.choices.get(name, None)
            if subparser is None:
                continue
            sparser = subparser.add_argument_group('JSON serialized based '
                                                   'varianter options')
            settings.register_option(section=name,
                                     key='json_variants_load',
                                     default=None,
                                     help_msg=help_msg,
                                     parser=sparser,
                                     long_arg='--json-variants-load')

    def run(self, config):
        pass


class JsonVariants(Varianter):

    """
    Processes the serialized file into variants
    """

    name = 'json variants'
    description = "JSON serialized based Varianter"
    variants = None

    def initialize(self, config):
        # Looks like this could be either 'run' or 'variants'
        subcommand = config.get('subcommand')
        load_variants = config.get('{}.json_variants_load'.format(subcommand))

        if load_variants is None:
            self.variants = _NO_VARIANTS
            return
        try:
            with open(load_variants, 'r') as var_file:
                self.variants = varianter.Varianter(state=json.load(var_file))
        except IOError:
            LOG_UI.error("JSON serialized file '%s' could not be found or "
                         "is not readable", load_variants)
            if config.get('subcommand') == 'run':
                sys.exit(exit_codes.AVOCADO_JOB_FAIL)
            else:
                sys.exit(exit_codes.AVOCADO_FAIL)

    def __iter__(self):
        if self.variants == _NO_VARIANTS:
            return
        elif self.variants is None:
            raise RuntimeError("Iterating Varianter before initialization is"
                               "not supported")

        for variant in self.variants.itertests():
            yield variant

    def __len__(self):
        if self.variants == _NO_VARIANTS:
            return 0
        elif self.variants is None:
            raise RuntimeError("Calling Varianter __len__ before"
                               "initialization is not supported")

        return len(self.variants)

    def update_defaults(self, defaults):
        pass

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
        if self.variants == _NO_VARIANTS:
            return ""

        out = []
        verbose = variants > 1
        if summary:
            # TODO: tree representation
            out.append("No tree representation for JSON serialized variants")

        if variants:
            out.append("JSON Serialized Variants (%i):" % len(self))
            for variant in self:
                paths = ', '.join([x.path for x in variant["variant"]])

                out.append('%sVariant %s:    %s' % ('\n' if verbose else '',
                                                    variant["variant_id"],
                                                    paths))
                if not verbose:
                    continue
                env = set()
                for node in variant["variant"]:
                    for key, value in node.environment.items():
                        origin = node.environment.origin[key].path
                        env.add(("%s:%s" % (origin, key), str(value)))
                if not env:
                    return out
                fmt = '    %%-%ds => %%s' % max([len(_[0]) for _ in env])
                for record in sorted(env):
                    out.append(fmt % record)

        return "\n".join(out)
