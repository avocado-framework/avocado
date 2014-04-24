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

"""Plugins basic structure."""


class Plugin(object):

    """
    Base class for plugins.

    You'll inherit from this to write you own plugins.
    """

    name = 'plugin'
    enabled = True

    def __init__(self):
        """Creates a new plugin instance."""
        self.name = self.__class__.name
        self.enabled = self.__class__.enabled
        self.configured = False

    def configure(self, app_parser, cmd_parser):
        """Configuration and argument parsing.

        :param app_parser: application parser, modify to add extra options.
        :param cmd_parser: subcommand parser, modify to add new subcommands.
        """
        raise NotImplementedError('Plugins must implement the method configure')

    def activate(self, app_args):
        """Activate plugin.

        :param app_args: the parsed arguments.
        """
        pass
