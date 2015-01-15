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
# Copyright: Red Hat Inc. 2015
# Author: Cleber Rosa <cleber@redhat.com>

from avocado.core import output
from avocado.plugins import plugin
from avocado.linux import distro as distro_utils


class DistroOptions(plugin.Plugin):

    """
    Implements the avocado 'distro' subcommand
    """

    name = 'distro'
    enabled = True

    def configure(self, parser):
        self.parser = parser.subcommands.add_parser(
            'distro',
            help='Shows detected Linux distribution')
        super(DistroOptions, self).configure(self.parser)

    def run(self, args):
        view = output.View()
        detected = distro_utils.detect()
        msg = 'Detected distribution: %s (%s) version %s release %s' % (
            detected.name,
            detected.arch,
            detected.version,
            detected.release)
        view.notify(event="message", msg=msg)
