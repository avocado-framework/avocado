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
import collections

from avocado.plugins import plugin
from avocado.core import output
from avocado.core import exit_codes
from avocado.core import tree
from avocado import multiplexer


class Multiplexer(plugin.Plugin):

    """
    Implements the avocado 'multiplex' subcommand.
    """

    name = 'multiplexer'
    enabled = True

    def configure(self, parser):
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

        self.parser.add_argument('-c', '--contents', action='store_true', default=False,
                                 help="Shows the variant's content (variables)")
        super(Multiplexer, self).configure(self.parser)

    def run(self, args):
        view = output.View(app_args=args)
        multiplex_files = tuple(os.path.abspath(_)
                                for _ in args.multiplex_files)
        for path in multiplex_files:
            if not os.path.isfile(path):
                view.notify(event='error',
                            msg='Invalid multiplex file %s' % path)
                sys.exit(exit_codes.AVOCADO_JOB_FAIL)

        if args.tree:
            view.notify(event='message', msg='Config file tree structure:')
            t = tree.create_from_yaml(multiplex_files)
            t = tree.apply_filters(t, args.filter_only, args.filter_out)
            view.notify(event='minor', msg=t.get_ascii())
            sys.exit(exit_codes.AVOCADO_ALL_OK)

        variants = multiplexer.multiplex_yamls(multiplex_files,
                                               args.filter_only,
                                               args.filter_out)

        view.notify(event='message', msg='Variants generated:')
        for (index, tpl) in enumerate(variants):
            paths = ', '.join([x.path for x in tpl])
            view.notify(event='minor', msg='Variant %s:    %s' %
                        (index + 1, paths))
            if args.contents:
                env = collections.OrderedDict()
                for node in tpl:
                    env.update(node.environment)
                for k in sorted(env.keys()):
                    view.notify(event='minor', msg='    %s: %s' % (k, env[k]))

        sys.exit(exit_codes.AVOCADO_ALL_OK)
