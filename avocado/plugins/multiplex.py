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
        parser.add_argument("--summary", type=int, help="Verbosity of "
                            "the variants summary.")
        parser.add_argument("--variants", type=int, help="Verbosity of "
                            "the list of variants.")
        parser.add_argument('--system-wide', action='store_false',
                            default=True, dest="variants-skip-defaults",
                            help="Combine the files with the default "
                            "tree.")
        parser.add_argument('-c', '--contents', action='store_true',
                            default=False, help="[obsoleted by --variants] "
                            "Shows the node content (variables)")
        env_parser = parser.add_argument_group("environment view options")
        env_parser.add_argument('-d', '--debug', action='store_true',
                                dest="mux_debug", default=False,
                                help="Debug the multiplex tree.")
        tree_parser = parser.add_argument_group("tree view options")
        tree_parser.add_argument('-t', '--tree', action='store_true',
                                 default=False, help='[obsoleted by --summary]'
                                 ' Shows the multiplex tree structure')
        tree_parser.add_argument('-i', '--inherit', action="store_true",
                                 help="[obsoleted by --summary] Show the "
                                 "inherited values")

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
        varianter = args.avocado_variants
        try:
            varianter.parse(args)
        except (IOError, ValueError) as details:
            log.error("Unable to parse varianter: %s", details)
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)
        use_utf8 = settings.get_value("runner.output", "utf8",
                                      key_type=bool, default=None)
        summary = args.summary or 0
        variants = args.variants or 0

        # Parse obsolete options (unsafe to combine them with new args)
        if args.tree:
            summary += 1
            if args.contents:
                summary += 1
            if args.inherit:
                summary += 2
        else:
            if args.contents:
                variants += 2

        # When nothing is specified, show variants
        if not summary and not variants:
            variants = 1

        # Produce the output
        lines = args.avocado_variants.to_str(summary=summary,
                                             variants=variants,
                                             use_utf8=use_utf8)
        for line in lines.splitlines():
            log.debug(line)

        sys.exit(exit_codes.AVOCADO_ALL_OK)
