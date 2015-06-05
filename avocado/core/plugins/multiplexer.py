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

from avocado.core.plugins import plugin
from avocado.core import output
from avocado.core import exit_codes
from avocado.core import tree
from avocado.core import multiplexer


class Multiplexer(plugin.Plugin):

    """
    Implements the avocado 'multiplex' subcommand
    """

    name = 'multiplexer'
    enabled = True

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

        self.parser.add_argument('-t', '--tree', action='store_true', default=False,
                                 help='Shows the multiplex tree structure')
        self.parser.add_argument('--attr', nargs='*', default=[],
                                 help="Which attributes to show when using "
                                 "--tree (default is 'name')")
        self.parser.add_argument('-c', '--contents', action='store_true', default=False,
                                 help="Shows the variant content (variables)")
        self.parser.add_argument('-d', '--debug', action='store_true',
                                 default=False, help="Debug multiplexed "
                                 "files.")
        self.parser.add_argument('--env', default=[], nargs='*')
        super(Multiplexer, self).configure(self.parser)

    def activate(self, args):
        # Extend default multiplex tree of --env values
        for value in getattr(args, "env", []):
            value = value.split(':', 2)
            if len(value) < 2:
                raise ValueError("key:value pairs required, found only %s"
                                 % (value))
            elif len(value) == 2:
                args.default_multiplex_tree.value[value[0]] = value[1]
            else:
                node = args.default_multiplex_tree.get_node(value[0], True)
                node.value[value[1]] = value[2]

    def run(self, args):
        view = output.View(app_args=args)
        try:
            mux_tree = multiplexer.yaml2tree(args.multiplex_files,
                                             args.filter_only, args.filter_out,
                                             args.debug)
        except IOError, details:
            view.notify(event='error',
                        msg=details.strerror)
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)
        mux_tree.merge(args.default_multiplex_tree)
        if args.tree:
            view.notify(event='message', msg='Config file tree structure:')
            view.notify(event='minor',
                        msg=mux_tree.get_ascii(attributes=args.attr))
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
                env = {}
                for node in tpl:
                    env.update(node.environment)
                for k in sorted(env.keys()):
                    view.notify(event='minor', msg='    %s: %s' % (k, env[k]))

        sys.exit(exit_codes.AVOCADO_ALL_OK)
