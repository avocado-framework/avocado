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

"""
The core Avocado application.
"""

import os

from avocado.core.parser import Parser
from avocado.plugins.manager import get_plugin_manager


class AvocadoApp(object):

    """
    Avocado application.
    """

    def __init__(self, external_plugins=None):

        # Catch all libc runtime errors to STDERR
        os.environ['LIBC_FATAL_STDERR_'] = '1'

        self.external_plugins = external_plugins
        self.plugin_manager = None
        self.parser = Parser()
        self.parser.start()
        self.load_plugin_manager(self.parser.args.plugins_dir)
        self.ready = True
        try:
            self.parser.resume()
            self.plugin_manager.activate(self.parser.args)
            self.parser.finish()
        except IOError:
            self.ready = False

    def load_plugin_manager(self, plugins_dir):
        """Load Plugin Manager.

        :param plugins_dir: Extra plugins directory.
        """
        self.plugin_manager = get_plugin_manager()
        self.plugin_manager.load_plugins(plugins_dir)
        if self.external_plugins:
            self.plugin_manager.add_plugins(self.external_plugins)
        self.plugin_manager.configure(self.parser)

    def run(self):
        if self.ready:
            return self.parser.take_action()
