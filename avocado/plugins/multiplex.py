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
from avocado.core import multiplexer
from avocado.core import tree
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.settings import settings


class Multiplex(CLICmd):

    """
    Implements the avocado 'multiplex' subcommand
    """

    name = 'multiplex'
    description = 'Generate a list of dictionaries with params from a multiplex file'

    def __init__(self, *args, **kwargs):
        super(Multiplex, self).__init__(*args, **kwargs)
        self._from_args_tree = tree.TreeNode()

    def configure(self, parser):
        if multiplexer.MULTIPLEX_CAPABLE is False:
            return

        parser = super(Multiplex, self).configure(parser)
        parser.add_argument('multiplex_files', nargs='+',
                            help='Path(s) to a multiplex file(s)')

        parser.add_argument('--filter-only', nargs='*', default=[],
                            help='Filter only path(s) from multiplexing')

        parser.add_argument('--filter-out', nargs='*', default=[],
                            help='Filter out path(s) from multiplexing')
        parser.add_argument('--system-wide', action='store_true',
                            help="Combine the files with the default "
                            "tree.")
        parser.add_argument('-c', '--contents', action='store_true',
                            default=False, help="Shows the node content "
                            "(variables)")
        parser.add_argument('-l', '--list', action='store_true',
                            default=False, help="Dump variants as yaml list")
        parser.add_argument('--list-variant-id', action='store_true',
                            default=False, help="Append variant id to list")

        parser.add_argument('--mux-inject', default=[], nargs='*',
                            help="Inject [path:]key:node values into "
                            "the final multiplex tree.")
        env_parser = parser.add_argument_group("environment view options")
        env_parser.add_argument('-d', '--debug', action='store_true',
                                default=False, help="Debug multiplexed "
                                "files.")
        tree_parser = parser.add_argument_group("tree view options")
        tree_parser.add_argument('-t', '--tree', action='store_true',
                                 default=False, help='Shows the multiplex '
                                 'tree structure')
        tree_parser.add_argument('-i', '--inherit', action="store_true",
                                 help="Show the inherited values")

    def _activate(self, args):
        # Extend default multiplex tree of --env values
        for value in getattr(args, "mux_inject", []):
            value = value.split(':', 2)
            if len(value) < 2:
                raise ValueError("key:value pairs required, found only %s"
                                 % (value))
            elif len(value) == 2:
                self._from_args_tree.value[value[0]] = value[1]
            else:
                node = self._from_args_tree.get_node(value[0], True)
                node.value[value[1]] = value[2]

    def run(self, args):
        self._activate(args)
        log = logging.getLogger("avocado.app")
        err = None
        if args.tree and args.debug:
            err = "Option --tree is incompatible with --debug."
        elif not args.tree and args.inherit:
            err = "Option --inherit can be only used with --tree"
        if err:
            log.error(err)
            sys.exit(exit_codes.AVOCADO_FAIL)
        try:
            mux_tree = multiplexer.yaml2tree(args.multiplex_files,
                                             args.filter_only, args.filter_out,
                                             args.debug)
        except IOError as details:
            log.error(details.strerror)
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)
        if args.system_wide:
            mux_tree.merge(args.default_avocado_params)
        mux_tree.merge(self._from_args_tree)
        if args.tree:
            if args.contents:
                verbose = 1
            else:
                verbose = 0
            if args.inherit:
                verbose += 2
            use_utf8 = settings.get_value("runner.output", "utf8",
                                          key_type=bool, default=None)
            log.debug(tree.tree_view(mux_tree, verbose, use_utf8))
            sys.exit(exit_codes.AVOCADO_ALL_OK)

        variants = multiplexer.MuxTree(mux_tree)
        if args.list:
            prefix = '  '
            for (index, tpl) in enumerate(variants):
                level = 0
                if args.list_variant_id:
                    log.info("variant: !mux")
                    level += 1

                lname = ''
                for x in tpl:
                    path = x.path[len('/run'):]
                    lname += path.replace('/', '-')
                # trim first '-'
                lname = lname[1:]
                if args.list_variant_id:
                    log.info('%s%d:' % (prefix * level, index))
                    level += 1
                log.info('%s%s:' % (prefix * level, lname))
                level += 1
                env = set()
                for node in tpl:
                    for key, value in node.environment.iteritems():
                        origin = node.environment_origin[key].path
                        env.add(("%s" % key, str(value)))
                if not env:
                    continue
                fmt = '%s  %%-%ds: %%s' % (prefix * level,
                                           max([len(_[0]) for _ in env]))
                for record in sorted(env):
                    log.info(fmt, *record)
                log.info("")

            sys.exit(exit_codes.AVOCADO_ALL_OK)

        log.info('Variants generated:')
        for (index, tpl) in enumerate(variants):
            if not args.debug:
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
