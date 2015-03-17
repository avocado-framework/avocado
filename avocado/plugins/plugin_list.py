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
# Author: Ruda Moura <rmoura@redhat.com>

from avocado.plugins import plugin
from avocado.plugins.manager import get_plugin_manager
from avocado.core import output


class PluginList(plugin.Plugin):

    """
    Implements the avocado 'plugins' subcommand
    """

    name = 'plugins_list'
    enabled = True

    def configure(self, parser):
        self.parser = parser.subcommands.add_parser(
            'plugins',
            help='List all plugins loaded')
        self.parser.add_argument('--disable-paginator',
                                 dest='disable_paginator',
                                 action='store_true',
                                 help='Disable paginator usage')
        super(PluginList, self).configure(self.parser)

    def run(self, args):
        view = output.View(app_args=args,
                           use_paginator=not args.disable_paginator)
        pm = get_plugin_manager()
        view.notify(event='message', msg='Plugins loaded:')
        blength = 0
        for plug in pm.plugins:
            clength = len(plug.name)
            if clength > blength:
                blength = clength

        format_str = "    %-" + str(blength) + "s %s %s"
        for plug in sorted(pm.plugins):
            if plug.enabled:
                status = "(Enabled)"
            else:
                status = "(Disabled)"
            view.notify(event='minor', msg=format_str % (plug.name, plug.description, status))
        view.cleanup()
