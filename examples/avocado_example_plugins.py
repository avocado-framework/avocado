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

from avocado.plugins import plugin
from avocado.plugins.manager import get_plugin_manager
from avocado.core import output


class HelloWorld(plugin.Plugin):

    """
    Hello World! plugin example.
    """

    def configure(self, parser):
        myparser = parser.add_parser('hello',
                                     help='Hello World! plugin example')
        myparser.set_defaults(func=self.hello)
        self.enabled = True

    def hello(self, args):
        print self.__doc__


class PluginsList(plugin.Plugin):

    """
    List all plugins loaded.
    """

    def configure(self, parser):
        myparser = parser.add_parser('plugins',
                                     help='List all plugins loaded')
        myparser.set_defaults(func=self.list_plugins)
        self.enabled = True

    def list_plugins(self, args):
        bcolors = output.colors
        pipe = output.get_paginator()
        pm = get_plugin_manager()
        pipe.write(bcolors.header_str('Plugins loaded:'))
        pipe.write('\n')
        for plug in pm.plugins:
            pipe.write('    %s - %s\n' % (plug, plug.__doc__))
