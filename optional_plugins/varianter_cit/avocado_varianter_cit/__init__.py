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

import copy
import itertools
import os
import random
import sys

from six import iteritems
from six.moves import configparser
from six.moves import zip

from avocado.core import exit_codes
from avocado.core import varianter
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLI
from avocado.core.plugin_interfaces import Varianter
from avocado.core.tree import TreeNode


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
                             metavar='ORDER', type=int, default=2,
                             help=("Order of combinations. Defaults to "
                                   "%(default)s, maximum number is specific "
                                   "to parameter file content"))

    def run(self, args):
        pass


class VarianterCit(Varianter):

    """
    Processes the parameters file into variants
    """

    name = 'cit'
    description = "CIT Varianter"

    def initialize(self, args):
        self.variants = None

        cit_parameter_file = getattr(args, "cit_parameter_file", None)
        if cit_parameter_file is None:
            return
        else:
            cit_parameter_file = os.path.expanduser(cit_parameter_file)
            if not os.access(cit_parameter_file, os.R_OK):
                LOG_UI.error("parameter file '%s' could not be found or "
                             "is not readable", cit_parameter_file)
                self.error_exit(args)

        config = configparser.ConfigParser()
        try:
            config.read(cit_parameter_file)
        except Exception as details:
            LOG_UI.error("Cannot parse parameter file: %s", details)
            self.error_exit(args)

        parameters = [(key, value.split(', '))
                      for key, value in config.items('parameters')]
        order = args.cit_order_of_combinations
        cit = Cit(parameters, order)
        self.headers, self.variants = cit.combine()

    @staticmethod
    def error_exit(args):
        if args.subcommand == 'run':
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
                   "variant": TreeNode('', variant),
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


class Cit(object):

    MATRIX_ROW_SIZE = 20
    MAX_ITERATIONS = 15

    def __init__(self, parameters, order):
        # Parameters come as ('key', ['value1', 'value2', 'value3'])
        self.parameters = parameters
        # Length (number of values) for each parameter
        self.parameters_length = [len(param[1]) for param in self.parameters]
        # Order of combinations
        self.order = min(order, len(parameters))
        self.hash_table = {}

    def combine(self):
        """
        Computes the combination of parameters

        :returns: headers (list of parameters keys) and combinations (list of
                  dictionaries. Each dictionary represents a combination of
                  parameters.
        :rtype: tuple
        """
        self.create_interaction_hash_table()
        final_list = self.create_final_list()

        headers = [item[0] for item in self.parameters]
        result = [[self.parameters[i][1][combination[i]]
                   for i in range(len(combination))]
                  for combination in final_list]
        combinations = []
        for combination in result:
            combinations.append(dict(zip(headers, combination)))

        return headers, combinations

    def create_interaction_hash_table(self):
        for c in itertools.combinations(range(len(self.parameters_length)), self.order):
            self.hash_table[c] = self.get_iteration(c)

    def create_final_list(self):
        final_list = []
        while len(self.hash_table) != 0:
            iterations = 0
            previous_test_case = []
            previous_remove_list = {}
            previous_weight = 0

            while iterations < self.MAX_ITERATIONS:
                max_width = len(self.hash_table)
                matrix = self.create_random_matrix()
                remove_list = {}
                for i in matrix:
                    width = self.get_weight(i, remove_list)
                    if width == 0 or width <= previous_weight:
                        remove_list.clear()
                        continue
                    elif width == max_width:
                        final_list.append(i)
                        self.remove_from_hash_table(remove_list)
                        previous_test_case = []
                        previous_remove_list = {}
                        continue
                    elif width > previous_weight:
                        previous_weight = width
                        previous_test_case = i
                        previous_remove_list = dict(remove_list)
                        remove_list.clear()
                iterations += 1
            if len(previous_test_case) != 0:
                previous_remove_list = self.neighborhood_search(
                    previous_test_case, previous_weight,
                    max_width, previous_remove_list)
                final_list.append(previous_test_case)
                self.remove_from_hash_table(previous_remove_list)
        return final_list

    def get_iteration(self, parameter_combination):
        parameters_array = []
        for c in parameter_combination:
            array = range(self.parameters_length[c])
            parameters_array.append(array)
        iterations = {}
        for i in itertools.product(*parameters_array):
            iterations[i] = tuple(i)
        return iterations

    def get_weight(self, test_case, remove_list):
        weight = 0
        for i in self.hash_table:
            iteration = tuple(test_case[j] for j in i)
            try:
                value = self.hash_table[i][iteration]
                weight += 1
                remove_list[i] = value
            except KeyError:
                continue

        return weight

    def remove_from_hash_table(self, remove_list):
        for i in remove_list:
            del self.hash_table[i][remove_list[i]]
            if len(self.hash_table[i]) == 0:
                self.hash_table.pop(i)
        remove_list.clear()

    def create_random_matrix(self):
        matrix = []
        for _ in range(self.MATRIX_ROW_SIZE):
            row = []
            for j in self.parameters_length:
                row.append(random.randint(0, j-1))
            matrix.append(row)
        return matrix

    def neighborhood_search(self, test_case, width, max_width, remove_list):
        neighborhood = list(test_case)
        neighborhood_remove_list = {}
        for i in range(len(test_case)):
            # neighborhood +1
            if (neighborhood[i] + 1) == self.parameters_length[i]:
                neighborhood[i] = 0
            else:
                neighborhood[i] += 1
            neighborhood_width = self.get_weight(neighborhood, neighborhood_remove_list)
            if neighborhood_width > width:
                width = neighborhood_width
                remove_list = copy.deepcopy(neighborhood_remove_list)
                del test_case[:]
                for j in neighborhood:
                    test_case.append(j)
                if neighborhood_width == max_width:
                    return remove_list
            if neighborhood[i] == 0:
                neighborhood[i] = self.parameters_length[i] - 1
            else:
                neighborhood[i] -= 1

            # neighborhood -1
            if neighborhood[i] == 0:
                neighborhood[i] = self.parameters_length[i] - 1
            else:
                neighborhood[i] -= 1
            neighborhood_width = self.get_weight(neighborhood, neighborhood_remove_list)
            if neighborhood_width > width:
                width = neighborhood_width
                remove_list = copy.deepcopy(neighborhood_remove_list)
                del test_case[:]
                for j in neighborhood:
                    test_case.append(j)
                if neighborhood_width == max_width:
                    return remove_list
            if (neighborhood[i] + 1) == self.parameters_length[i]:
                neighborhood[i] = 0
            else:
                neighborhood[i] += 1
        return remove_list
