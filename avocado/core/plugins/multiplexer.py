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

import os
import sys

from avocado.core.plugins import plugin
from avocado.core import output
from avocado.core import exit_codes
from avocado.core import tree
from avocado import multiplexer
import argparse


class Arg2Tree(argparse.Action):
    '''
    def __init__(self, option_strings, dest, nargs=None, const=None,
                 default=None, type=None, choices=None, required=False,
                 help=None, metavar=None):
        super(Arg2Tree, self).__init__(self, option_strings=option_strings,
                                       dest=dest, nargs=nargs, const=const,
                                       default=default, type=type,
                                       choices=choices, required=required,
                                       help=help, metavar=metavar)
    '''
    def __call__(self, parser, namespace, values, option_string=None):
        if not namespace.env:
            namespace.env = tree.TreeNode()
        for value in values:
            value = value.split(':', 2)
            print value
            if len(value) < 2:
                raise argparse.ArgumentError("key:value pairs required, found "
                                             "only value.")
            elif len(value) == 2:
                namespace.env.value[value[0]] = value[1]
            else:
                node = namespace.env.get_node(value[0], True)
                node.value[value[1]] = value[2]


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
        self.parser.add_argument('--env', action=Arg2Tree, nargs='*')
        super(Multiplexer, self).configure(self.parser)

    def run(self, args):
        view = output.View(app_args=args)
        multiplex_files = args.multiplex_files
        if args.tree:
            view.notify(event='message', msg='Config file tree structure:')
            try:
                t = tree.create_from_yaml(multiplex_files)
                if args.env:
                    t.merge(args.env)
            except IOError, details:
                view.notify(event='error', msg=details.strerror)
                sys.exit(exit_codes.AVOCADO_JOB_FAIL)
            t = tree.apply_filters(t, args.filter_only, args.filter_out)
            view.notify(event='minor',
                        msg=t.get_ascii(attributes=args.attr))
            sys.exit(exit_codes.AVOCADO_ALL_OK)

        try:
            variants = multiplexer.multiplex_yamls(multiplex_files,
                                                   args.filter_only,
                                                   args.filter_out,
                                                   args.debug,
                                                   additional_tree=args.env)
        except IOError, details:
            view.notify(event='error',
                        msg=details.strerror)
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)

        view.notify(event='message', msg='Variants generated:')
        for (index, tpl) in enumerate(variants):
            if not args.debug:
                paths = ', '.join([x.path for x in tpl])
            else:
                color = output.term_support.LOWLIGHT
                cend = output.term_support.ENDC
                paths = ', '.join(["%s%s@%s%s" % (_.name, color, _.yaml, cend)
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
