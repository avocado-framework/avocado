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
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

import logging
import sys

from avocado.core import exit_codes
from avocado.core import tree
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.settings import settings


class Multiplex(CLICmd):

    """
    Implements the avocado 'multiplex' subcommand
    """

    name = 'multiplex'
    description = "Tool to analyze and visualize test variants and params"

    def __init__(self, *args, **kwargs):
        super(Multiplex, self).__init__(*args, **kwargs)

    def configure(self, parser):
        parser = super(Multiplex, self).configure(parser)
        parser.add_argument('--system-wide', action='store_false',
                            default=True, dest="mux-skip-defaults",
                            help="Combine the files with the default "
                            "tree.")
        parser.add_argument('-c', '--contents', action='store_true',
                            default=False, help="Shows the node content "
                            "(variables)")
        env_parser = parser.add_argument_group("environment view options")
        env_parser.add_argument('-d', '--debug', action='store_true',
                                dest="mux_debug", default=False,
                                help="Debug the multiplex tree.")
        tree_parser = parser.add_argument_group("tree view options")
        tree_parser.add_argument('-t', '--tree', action='store_true',
                                 default=False, help='Shows the multiplex '
                                 'tree structure')
        tree_parser.add_argument('-i', '--inherit', action="store_true",
                                 help="Show the inherited values")

    def run(self, args):
        log = logging.getLogger("avocado.app")
        err = None
        if args.tree and args.mux_debug:
            err = "Option --tree is incompatible with --debug."
        elif not args.tree and args.inherit:
            err = "Option --inherit can be only used with --tree"
        if err:
            log.error(err)
            sys.exit(exit_codes.AVOCADO_FAIL)
        variants = args.avocado_variants
        try:
            variants.parse(args)
        except (IOError, ValueError) as details:
            log.error("Unable to parse variants: %s", details)
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)
        if args.tree:
            if args.contents:
                verbose = 1
            else:
                verbose = 0
            if args.inherit:
                verbose += 2
            use_utf8 = settings.get_value("runner.output", "utf8",
                                          key_type=bool, default=None)
            log.debug(tree.tree_view(variants.variants.root, verbose, use_utf8))
            sys.exit(exit_codes.AVOCADO_ALL_OK)

        log.info('Variants generated:')
        if args.mux_debug:
            # In this version `avocado_variants.debug` is not set properly,
            # let's force-enable it before calling str_variants_long to
            # get the expected results.
            args.avocado_variants.debug = True
        for line in args.avocado_variants.str_variants_long(True).splitlines():
            log.debug(line)

        sys.exit(exit_codes.AVOCADO_ALL_OK)
