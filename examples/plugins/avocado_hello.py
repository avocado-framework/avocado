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


class HelloWorld(plugin.Plugin):

    """
    The classical Hello World! plugin example.
    """

    name = 'hello_world'
    enabled = True

    def configure(self, parser):
        """
        Add the subparser for the 'hello' action.
        """
        self.parser = parser.subcommands.add_parser(
            'hello',
            help='Hello World! plugin example')
        super(HelloWorld, self).configure(self.parser)

    def run(self, args):
        """
        This method is called whenever we use the command 'hello'.
        """
        print self.__doc__
