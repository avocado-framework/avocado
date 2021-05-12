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

import logging
import os
import sys

from avocado_varianter_cit.Cit import LOG, Cit
from avocado_varianter_cit.Parser import Parser

from avocado.core import exit_codes, varianter
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLI, Varianter
from avocado.core.settings import settings
from avocado.core.tree import TreeNode

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
            subparser.add_argument_group('CIT varianter options')
            settings.register_option(section="{}.cit".format(name),
                                     key='parameter_file',
                                     metavar='PATH',
                                     help_msg='Paths to a parameter file',
                                     parser=subparser,
                                     default=None,
                                     long_arg='--cit-parameter-file')

            help_msg = "Order of combinations. Maximum number is 6"
            settings.register_option(section="{}.cit".format(name),
                                     key='combination_order',
                                     key_type=int,
                                     parser=subparser,
                                     help_msg=help_msg,
                                     metavar='ORDER',
                                     default=DEFAULT_ORDER_OF_COMBINATIONS,
                                     long_arg='--cit-order-of-combinations')

    def run(self, config):
        if config.get('variants.debug'):
            LOG.setLevel(logging.DEBUG)


class VarianterCit(Varianter):

    """
    Processes the parameters file into variants
    """

    name = 'cit'
    description = "CIT Varianter"

    def initialize(self, config):
        subcommand = config.get('subcommand')
        self.variants = None  # pylint: disable=W0201
        order = config.get("{}.cit.combination_order".format(subcommand))
        if order and order > 6:
            LOG_UI.error("The order of combinations is bigger then 6")
            self.error_exit(config)

        section_key = "{}.cit.parameter_file".format(subcommand)
        cit_parameter_file = config.get(section_key)
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
        except ValueError as details:
            LOG_UI.error("Cannot parse parameter file: %s", details)
            self.error_exit(config)

        input_data = [len(parameter[1]) for parameter in parameters]

        cit = Cit(input_data, order, constraints)
        final_list = cit.compute()
        self.headers = [parameter[0] for parameter in parameters]  # pylint: disable=W0201
        results = [[parameters[j][1][final_list[i][j]] for j in range(len(final_list[i]))]
                   for i in range(len(final_list))]
        self.variants = []  # pylint: disable=W0201
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
