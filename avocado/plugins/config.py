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

from avocado.plugins import plugin
from avocado.core import output
from avocado.settings import settings


class ConfigOptions(plugin.Plugin):

    """
    Implements the avocado 'config' subcommand
    """

    name = 'config'
    enabled = True

    def configure(self, parser):
        self.parser = parser.subcommands.add_parser(
            'config',
            help='Shows avocado config keys')
        super(ConfigOptions, self).configure(self.parser)

    def run(self, args):
        view = output.View()
        view.notify(event="message", msg='Config file path: %s' % settings.config_path)
        view.notify(event="minor", msg='')
        blength = 0
        for section in settings.config.sections():
            for value in settings.config.items(section):
                clength = len('%s.%s' % (section, value[0]))
                if clength > blength:
                    blength = clength

        format_str = "    %-" + str(blength) + "s %s"

        view.notify(event="minor", msg=format_str % ('Section.Key', 'Value'))
        for section in settings.config.sections():
            for value in settings.config.items(section):
                config_key = ".".join((section, value[0]))
                view.notify(event="minor", msg=format_str % (config_key, value[1]))
