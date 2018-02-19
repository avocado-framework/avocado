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

from six import iteritems

from avocado.core import exit_codes
from avocado.core import tree
from avocado.core import varianter
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLI
from avocado.core.plugin_interfaces import Varianter


class VarianterSerializedCLI(CLI):

    """
    Serialized based Varianter options
    """

    name = 'serialized'
    description = "Serialized based Varianter options for the 'run' subcommand"

    def configure(self, parser):

        for name in ("run", "variants"):  # intentionally omitting "multiplex"
            subparser = parser.subcommands.choices.get(name, None)
            if subparser is None:
                continue
            sparser = subparser.add_argument_group('json serialized varianter '
                                                   'options')
            sparser.add_argument('--load-variants', default=None,
                                 help=('Load the Variants from a JSON '
                                       'serialized file'))

    def run(self, args):
        pass


class VarianterSerialized(Varianter):

    """
    Processes the serialized file into variants
    """

    name = 'serialized'
    description = "JSON Serialized Varianter"

    def initialize(self, args):
        self.variants = None
        load_variants = getattr(args, "load_variants", None)

        if load_variants is None:
            return
        try:
            with open(load_variants, 'r') as var_file:
                self.variants = varianter.Varianter(state=json.load(var_file))
        except IOError:
            LOG_UI.error("JSON serialized file '%s' could not be found or "
                         "is not readable", load_variants)
            if args.subcommand == 'run':
                sys.exit(exit_codes.AVOCADO_JOB_FAIL)
            else:
                sys.exit(exit_codes.AVOCADO_FAIL)

    def __iter__(self):
        if self.variants is None:
            return ''

        return self.variants.itertests()

    def __len__(self):
        if self.variants is None:
            return 0

        return self.variants._no_variants

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
        if not self.variants:
            return ""

        out = []
        verbose = variants > 1
        if summary:
            # Log tree representation
            out.append("No tree representation for serialized variants")
        else:
            out.append("Serialized Variants (%i):" % len(self))
            for variant in self:
                paths = ', '.join([x.path for x in variant["variant"]])

                out.append('%sVariant %s:    %s' % ('\n' if verbose else '',
                                                    variant["variant_id"],
                                                    paths))
                if not verbose:
                    continue
                env = set()
                for node in variant["variant"]:
                    for key, value in iteritems(node.environment):
                        origin = node.environment.origin[key].path
                        env.add(("%s:%s" % (origin, key), str(value)))
                if not env:
                    return out
                fmt = '    %%-%ds => %%s' % max([len(_[0]) for _ in env])
                for record in sorted(env):
                    out.append(fmt % record)

        return "\n".join(out)
