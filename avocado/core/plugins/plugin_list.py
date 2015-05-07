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

from avocado.core import output
from avocado.core.plugins import plugin
from avocado.core.plugins.builtin import ErrorsLoading
from avocado.core.plugins.manager import get_plugin_manager


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
        self.parser.add_argument('--paginator',
                                 choices=('on', 'off'), default='on',
                                 help='Turn the paginator on/off. '
                                      'Current: %(default)s')
        super(PluginList, self).configure(self.parser)

    def run(self, args):
        view = output.View(app_args=args,
                           use_paginator=args.paginator == 'on')
        pm = get_plugin_manager()

        enabled = [p for p in pm.plugins if p.enabled]
        disabled = [p for p in pm.plugins if not p.enabled]

        blength = 0
        for plug in pm.plugins:
            clength = len(plug.name)
            if clength > blength:
                blength = clength
        for load_error in ErrorsLoading:
            clength = len(load_error[0])
            if clength > blength:
                blength = clength
        format_str = "    %-" + str(blength + 1) + "s %s"

        if enabled:
            view.notify(event='message', msg=output.term_support.healthy_str("Plugins enabled:"))
            for plug in sorted(enabled):
                view.notify(event='minor', msg=format_str % (plug.name, plug.description))

        if disabled:
            view.notify(event='message', msg=output.term_support.fail_header_str('Plugins disabled:'))
            for plug in sorted(disabled):
                view.notify(event='minor', msg=format_str % (plug.name, "Disabled during plugin configuration"))

        if ErrorsLoading:
            view.notify(event='message', msg=output.term_support.fail_header_str('Unloadable plugin modules:'))
            for load_error in sorted(ErrorsLoading):
                view.notify(event='minor', msg=format_str % (load_error[0], load_error[1]))

        view.cleanup()
