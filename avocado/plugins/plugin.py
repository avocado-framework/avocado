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

    name = 'noname'
    enabled = False

    def __init__(self, name=None, enabled=None):
        """Creates a new plugin instance.

        :param name: plugin short name.
        :param enabled: plugin status: enabled or not.
        """
        if name is not None:
            self.name = name
        if enabled is not None:
            self.enabled = enabled
        if self.__doc__ is not None:
            self.description = self.__doc__.strip()
        else:
            self.description = 'There is no description for this plugin'
        self.configured = False

    def __repr__(self):
        return "%s(name='%s')" % (self.__class__.__name__, self.name)

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
