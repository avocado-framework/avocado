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
from avocado.core import error_codes
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
        self.parser.add_argument('multiplex_file', type=str, nargs='?', default=None,
                                 help='Path to a multiplex file')

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

        if not args.multiplex_file:
            view.notify(event='error', msg='A multiplex file is required, aborting...')
            sys.exit(error_codes.numeric_status['AVOCADO_JOB_FAIL'])

        multiplex_file = os.path.abspath(args.multiplex_file)

        if not os.path.isfile(multiplex_file):
            view.notify(event='error', msg='Invalid multiplex file %s' % multiplex_file)
            sys.exit(error_codes.numeric_status['AVOCADO_JOB_FAIL'])

        if args.tree:
            view.notify(event='message', msg='Config file tree structure:')
            t = tree.create_from_yaml(open(multiplex_file))
            t = tree.apply_filters(t, args.filter_only, args.filter_out)
            view.notify(event='minor', msg=t.get_ascii())
            sys.exit(error_codes.numeric_status['AVOCADO_ALL_OK'])

        variants = multiplexer.create_variants_from_yaml(open(multiplex_file),
                                                         args.filter_only,
                                                         args.filter_out)

        view.notify(event='message', msg='Variants generated:')
        for (index, tpl) in enumerate(variants):
            paths = ', '.join([x.path for x in tpl])
            view.notify(event='minor', msg='Variant %s:    %s' % (index+1, paths))
            if args.contents:
                env = collections.OrderedDict()
                for node in tpl:
                    env.update(node.environment)
                for k in sorted(env.keys()):
                    view.notify(event='minor', msg='    %s: %s' % (k, env[k]))

        sys.exit(error_codes.numeric_status['AVOCADO_ALL_OK'])
