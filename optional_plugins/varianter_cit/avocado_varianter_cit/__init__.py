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
# Authors: Amador Pahim <amador@pahim.org>
#          Bestoun S. Ahmed <bestoon82@gmail.com>
#          Cleber Rosa <crosa@redhat.com>

import os
import sys
import logging

from avocado.core import exit_codes
from avocado.core import varianter
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLI
from avocado.core.plugin_interfaces import Varianter
from avocado.core.tree import TreeNode
from avocado_varianter_cit.Cit import Cit, LOG
from avocado_varianter_cit.Parser import Parser


#: The default order of combinations
DEFAULT_ORDER_OF_COMBINATIONS = 2


class VarianterCitCLI(CLI):

    """
    CIT Varianter options
    """

    name = 'cit'
    description = "CIT Varianter options for the 'run' subcommand"

    def configure(self, parser):

        for name in ("run", "variants"):
            subparser = parser.subcommands.choices.get(name, None)
            if subparser is None:
                continue
            cit = subparser.add_argument_group('CIT varianter options')
            cit.add_argument('--cit-parameter-file', metavar='PATH',
                             help="Paths to a parameter file")
            cit.add_argument('--cit-order-of-combinations',
                             metavar='ORDER', type=int,
                             default=DEFAULT_ORDER_OF_COMBINATIONS,
                             help=("Order of combinations. Defaults to "
                                   "%(default)s, maximum number is 6"))

    def run(self, config):
        if config.get("varianter_debug", False):
            LOG.setLevel(logging.DEBUG)


class VarianterCit(Varianter):

    """
    Processes the parameters file into variants
    """

    name = 'cit'
    description = "CIT Varianter"

    def initialize(self, config):
        self.variants = None
        order = config.get('cit_order_of_combinations', DEFAULT_ORDER_OF_COMBINATIONS)
        if order > 6:
            LOG_UI.error("The order of combinations is bigger then 6")
            self.error_exit(config)

        cit_parameter_file = config.get("cit_parameter_file", None)
        if cit_parameter_file is None:
            return
        else:
            cit_parameter_file = os.path.expanduser(cit_parameter_file)
            if not os.access(cit_parameter_file, os.R_OK):
                LOG_UI.error("parameter file '%s' could not be found or "
                             "is not readable", cit_parameter_file)
                self.error_exit(config)

        try:
            parameters, constraints = Parser.parse(open(cit_parameter_file))
        except Exception as details:
            LOG_UI.error("Cannot parse parameter file: %s", details)
            self.error_exit(config)

        input_data = [parameter.get_size() for parameter in parameters]

        cit = Cit(input_data, order, constraints)
        final_list = cit.compute()
        self.headers = [parameter.name for parameter in parameters]
        results = [[parameters[j].values[final_list[i][j]] for j in range(len(final_list[i]))]
                   for i in range(len(final_list))]
        self.variants = []
        for combination in results:
            self.variants.append(dict(zip(self.headers, combination)))

    @staticmethod
    def error_exit(config):
        if config.get('subcommand') == 'run':
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)
        else:
            sys.exit(exit_codes.AVOCADO_FAIL)

    def __iter__(self):
        if self.variants is None:
            return

        variant_ids = []
        for variant in self.variants:
            variant_ids.append("-".join([variant.get(key)
                                         for key in self.headers]))

        for vid, variant in zip(variant_ids, self.variants):
            yield {"variant_id": vid,
                   "variant": [TreeNode('', variant)],
                   "paths": ['/']}

    def __len__(self):
        return sum(1 for _ in self.variants) if self.variants else 0

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

        if variants:
            # variants == 0 means disable, but in plugin it's brief
            out.append("CIT Variants (%s):" % len(self))
            for variant in self:
                out.extend(varianter.variant_to_str(variant, variants - 1,
                                                    kwargs, False))
        return "\n".join(out)
