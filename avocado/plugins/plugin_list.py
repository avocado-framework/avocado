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

from avocado.plugins.builtin import ErrorsLoading
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
        self.parser.add_argument('--paginator',
                                 choices=('on', 'off'), default='on',
                                 help='Turn the paginator on/off. '
                                      'Current: %(default)s')
        super(PluginList, self).configure(self.parser)

    def run(self, args):
        def _get_status(plugin_instance):
            if plugin_instance.enabled:
                status_str = output.term_support.healthy_str("(Enabled)")
            else:
                status_str = output.term_support.fail_header_str("(Disabled)")
            return status_str

        view = output.View(app_args=args,
                           use_paginator=args.paginator == 'on')
        pm = get_plugin_manager()

        enabled = [p for p in pm.plugins if p.enabled]
        disabled = [p for p in pm.plugins if not p.enabled]

        blength = 0

        combined_list = pm.plugins + ErrorsLoading
        for plug in combined_list:
            clength = len(plug.name)
            if clength > blength:
                blength = clength

        format_str = "    %-" + str(blength) + "s %s %s"

        if enabled:
            view.notify(event='message', msg='Plugins enabled:')
            view.notify(event='minor', msg=format_str % ("Name", "Description", ""))
            for plug in sorted(enabled):
                view.notify(event='minor', msg=format_str % (plug.name, plug.description, _get_status(plug)))

        if disabled:
            view.notify(event='message', msg='Plugins disabled:')
            view.notify(event='minor', msg=format_str % ("Name", "Reason", ""))
            for plug in sorted(disabled):
                view.notify(event='minor', msg=format_str % (plug.name, plug.disable_reason, _get_status(plug)))

        if ErrorsLoading:
            view.notify(event='message', msg='Plugins that failed to load (bugs/missing libs):')
            view.notify(event='minor', msg=format_str % ("Module", "Reason", ""))
            for plug in sorted(ErrorsLoading):
                view.notify(event='minor', msg=format_str % (plug.name, plug.disable_reason, _get_status(plug)))

        view.cleanup()
