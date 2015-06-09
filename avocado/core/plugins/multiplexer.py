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

import sys

from .. import multiplexer
from .. import exit_codes
from .. import output
from .. import tree
from . import plugin
from ..settings import settings


class Multiplexer(plugin.Plugin):

    """
    Implements the avocado 'multiplex' subcommand
    """

    name = 'multiplexer'
    enabled = True

    def __init__(self, *args, **kwargs):
        super(Multiplexer, self).__init__(*args, **kwargs)
        self._from_args_tree = tree.TreeNode()

    def configure(self, parser):
        if multiplexer.MULTIPLEX_CAPABLE is False:
            self.enabled = False
            return
        self.parser = parser.subcommands.add_parser(
            'multiplex',
            help='Generate a list of dictionaries with params from a multiplex file')
        self.parser.add_argument('multiplex_files', nargs='+',
                                 help='Path(s) to a multiplex file(s)')

        self.parser.add_argument('--filter-only', nargs='*', default=[],
                                 help='Filter only path(s) from multiplexing')

        self.parser.add_argument('--filter-out', nargs='*', default=[],
                                 help='Filter out path(s) from multiplexing')
        self.parser.add_argument('-s', '--system-wide', action='store_true',
                                 help="Combine the files with the default "
                                 "tree.")
        self.parser.add_argument('-c', '--contents', action='store_true',
                                 default=False, help="Shows the node content "
                                 "(variables)")
        self.parser.add_argument('--env', default=[], nargs='*',
                                 help="Inject [path:]key:node values into "
                                 "the final multiplex tree.")
        env_parser = self.parser.add_argument_group("environment view options")
        env_parser.add_argument('-d', '--debug', action='store_true',
                                default=False, help="Debug multiplexed "
                                "files.")
        tree_parser = self.parser.add_argument_group("tree view options")
        tree_parser.add_argument('-t', '--tree', action='store_true',
                                 default=False, help='Shows the multiplex '
                                 'tree structure')
        tree_parser.add_argument('-i', '--inherit', action="store_true",
                                 help="Show the inherited values")
        super(Multiplexer, self).configure(self.parser)

    def activate(self, args):
        # Extend default multiplex tree of --env values
        for value in getattr(args, "env", []):
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
        view = output.View(app_args=args)
        err = None
        if args.tree and args.debug:
            err = "Option --tree is incompatible with --debug."
        elif not args.tree and args.inherit:
            err = "Option --inherit can be only used with --tree"
        if err:
            view.notify(event="minor", msg=self.parser.format_help())
            view.notify(event="error", msg=err)
            sys.exit(exit_codes.AVOCADO_FAIL)
        try:
            mux_tree = multiplexer.yaml2tree(args.multiplex_files,
                                             args.filter_only, args.filter_out,
                                             args.debug)
        except IOError, details:
            view.notify(event='error',
                        msg=details.strerror)
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)
        if args.system_wide:
            mux_tree.merge(args.default_multiplex_tree)
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
            view.notify(event='minor', msg=tree.tree_view(mux_tree, verbose,
                                                          use_utf8))
            sys.exit(exit_codes.AVOCADO_ALL_OK)

        variants = multiplexer.MuxTree(mux_tree)
        view.notify(event='message', msg='Variants generated:')
        for (index, tpl) in enumerate(variants):
            if not args.debug:
                paths = ', '.join([x.path for x in tpl])
            else:
                color = output.term_support.LOWLIGHT
                cend = output.term_support.ENDC
                paths = ', '.join(["%s%s@%s%s" % (_.name, color,
                                                  getattr(_, 'yaml',
                                                          "Unknown"),
                                                  cend)
                                   for _ in tpl])
            view.notify(event='minor', msg='%sVariant %s:    %s' %
                        (('\n' if args.contents else ''), index + 1, paths))
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
                    view.notify(event='minor', msg=fmt % record)

        sys.exit(exit_codes.AVOCADO_ALL_OK)
