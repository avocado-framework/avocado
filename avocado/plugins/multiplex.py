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

from avocado.core import exit_codes, output
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

        parser.add_argument('--filter-only', nargs='*', default=[],
                            help='Filter only path(s) from multiplexing')

        parser.add_argument('--filter-out', nargs='*', default=[],
                            help='Filter out path(s) from multiplexing')
        parser.add_argument('--system-wide', action='store_false',
                            default=True, dest="mux-skip-defaults",
                            help="Combine the files with the default "
                            "tree.")
        parser.add_argument('-c', '--contents', action='store_true',
                            default=False, help="Shows the node content "
                            "(variables)")
        parser.add_argument('--mux-inject', default=[], nargs='*',
                            help="Inject [path:]key:node values into "
                            "the final multiplex tree.")
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
        mux = args.mux
        try:
            mux.parse(args)
        except (IOError, ValueError) as details:
            log.error("Unable to parse mux: %s", details)
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
            log.debug(tree.tree_view(mux.variants.root, verbose, use_utf8))
            sys.exit(exit_codes.AVOCADO_ALL_OK)

        log.info('Variants generated:')
        for (index, tpl) in enumerate(mux.variants):
            if not args.mux_debug:
                paths = ', '.join([x.path for x in tpl])
            else:
                color = output.TERM_SUPPORT.LOWLIGHT
                cend = output.TERM_SUPPORT.ENDC
                paths = ', '.join(["%s%s@%s%s" % (_.name, color,
                                                  getattr(_, 'yaml',
                                                          "Unknown"),
                                                  cend)
                                   for _ in tpl])
            log.debug('%sVariant %s:    %s', '\n' if args.contents else '',
                      index + 1, paths)
            if args.contents:
                env = set()
                for node in tpl:
                    for key, value in node.environment.iteritems():
                        origin = node.environment_origin[key].path
                        env.add(("%s:%s" % (origin, key), str(value)))
                if not env:
                    continue
                fmt = '    %%-%ds => %%s' % max([len(_[0]) for _ in env])
                for record in sorted(env):
                    log.debug(fmt, *record)

        sys.exit(exit_codes.AVOCADO_ALL_OK)
