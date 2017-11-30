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
# Copyright: Red Hat Inc. 2017
# Authors: Cleber Rosa <crosa@redhat.com>

import hashlib
import itertools
import os
import sys

from avocado.core import exit_codes
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLI
from avocado.core.plugin_interfaces import Varianter
from avocado.core.tree import TreeNode
from avocado.utils import path as utils_path
from avocado.utils import process


class VarianterPictCLI(CLI):

    """
    Pict based Varianter options
    """

    name = 'pict'
    description = "PICT based Varianter options for the 'run' subcommand"

    def configure(self, parser):
        try:
            pict_binary = utils_path.find_command('pict')
        except utils_path.CmdNotFoundError:
            pict_binary = None

        for name in ("run", "variants"):  # intentionally ommiting "multiplex"
            subparser = parser.subcommands.choices.get(name, None)
            if subparser is None:
                continue
            pict = subparser.add_argument_group('pict based varianter options')
            pict.add_argument('--pict-binary', metavar='PATH',
                              default=pict_binary,
                              help=('Where to find the binary version of the '
                                    'pict tool. Tip: download it from '
                                    'https://github.com/Microsoft/pict and '
                                    'run `make` to build it'))
            pict.add_argument('--pict-parameter-file', metavar='PATH',
                              help=("Paths to a pict parameter file"))
            pict.add_argument('--pict-parameter-path', metavar='PATH',
                              default='/run',
                              help=('Default path for parameters generated '
                                    'on the Pict based variants'))
            pict.add_argument('--pict-order-of-combinations',
                              metavar='ORDER', type=int, default=2,
                              help=("Order of combinations. Defaults to "
                                    "%(default)s, maximum number is specific "
                                    "to parameter file content"))

    def run(self, args):
        pass


def run_pict(binary, parameter_file, order):
    cmd = "%s %s /o:%s" % (binary, parameter_file, order)
    return process.system_output(cmd, shell=True)


def parse_pict_output(output):
    variants = []
    lines = output.splitlines()
    header = lines[0]
    headers = header.split('\t')
    for line in lines[1:]:
        variants.append(dict(zip(headers, line.split('\t'))))
    return (headers, variants)


class VarianterPict(Varianter):

    """
    Processes the pict file into variants
    """

    name = 'pict'
    description = "PICT based Varianter"

    def initialize(self, args):
        self.variants = None
        error = False

        pict_parameter_file = getattr(args, "pict_parameter_file", None)
        if pict_parameter_file is None:
            return
        else:
            pict_parameter_file = os.path.expanduser(pict_parameter_file)
            if not os.access(pict_parameter_file, os.R_OK):
                LOG_UI.error("pict parameter file '%s' could not be found or "
                             "is not readable", pict_parameter_file)
                error = True

        pict_binary = getattr(args, "pict_binary", None)
        if pict_binary is None:
            LOG_UI.error("pict binary could not be found in $PATH. Please set "
                         "its location with --pict-binary or put it in your "
                         "$PATH")
            error = True
        else:
            pict_binary = os.path.expanduser(pict_binary)
            if not os.access(pict_binary, os.R_OK | os.X_OK):
                LOG_UI.error("pict binary '%s' can not be executed, please check "
                             "the option given with --pict-binary and/or the file "
                             "permissions", pict_binary)
                error = True

        if error:
            if args.subcommand == 'run':
                sys.exit(exit_codes.AVOCADO_JOB_FAIL)
            else:
                sys.exit(exit_codes.AVOCADO_FAIL)

        self.parameter_path = getattr(args, "pict_parameter_path")

        output = run_pict(pict_binary,
                          pict_parameter_file,
                          getattr(args, "pict_order_of_combinations"))
        self.headers, self.variants = parse_pict_output(output)

    def __iter__(self):
        if self.variants is None:
            return

        variant_ids = []
        for variant in self.variants:
            base_id = "-".join([variant.get(key) for key in self.headers])
            variant_ids.append(base_id + '-' +
                               hashlib.sha1(base_id).hexdigest()[:4])

        for vid, variant in itertools.izip(variant_ids, self.variants):
            variant_tree_nodes = []
            for key, val in variant.items():
                variant_tree_nodes.append(TreeNode(key, {key: val}))

            yield {"variant_id": vid,
                   "variant": variant_tree_nodes,
                   "mux_path": self.parameter_path}

    def __len__(self):
        return sum(1 for _ in self)

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
        out = []
        if variants:
            out.append("Pict Variants (%i):" % len(self))
            for variant in self:
                out.append('Variant %s:    %s' % (variant["variant_id"],
                                                  self.parameter_path))
        return "\n".join(out)
