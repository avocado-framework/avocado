# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: RedHat 2013-2014
# Author: Ruda Moura <rmoura@redhat.com>

"""Plugins basic structure."""


class Plugin(object):

    """
    Base class for plugins.

    You'll inherit from this to write you own plugins.
    """

    def __init__(self, name=None, enabled=False):
        """Creates a new plugin instance.

        :param name: plugin name
        :param enabled: enabled/disabled status
        """
        if name is None:
            name = self.__class__.__name__.lower()
        self.name = name
        self.enabled = enabled

    def configure(self, parser):
        """Configuration and argument parsing.

        :param parser: a subparser of `ArgumentParser`
        """
        raise NotImplementedError('Plugins must implement the method configure')
