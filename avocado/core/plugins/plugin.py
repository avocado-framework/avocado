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

import os
import sys

"""Plugins basic structure."""


class Plugin(object):

    """
    Base class for plugins.

    You'll inherit from this to write you own plugins.
    """

    name = 'noname'
    enabled = False
    priority = 3
    parser = None

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

    def get_resource_path(self, *args):
        """
        Get the path of a plugin resource (static files, templates, etc).

        :param args: Path components (plugin resources dir is the root).
        :return: Full resource path.
        """
        plugins_dir = os.path.dirname(sys.modules[__name__].__file__)
        resources_dir = os.path.join(plugins_dir, 'resources', self.name)
        return os.path.join(resources_dir, *args)

    def configure(self, parser):
        """Configuration and argument parsing.

        :param parser: an instance of :class:`avocado.core.parser.Parser`

        To create a runner plugin, just call this method with `super()`.
        To create a result plugin, just set `configure` to `True`.
        """
        parser.set_defaults(dispatch=self.run)
        self.configured = True

    def activate(self, arguments):
        """Activate plugin.

        :param arguments: the parsed arguments.
        """
        pass

    def run(self, arguments):
        """
        Run plugin.

        :param arguments: the parsed arguments.
        """
        pass
