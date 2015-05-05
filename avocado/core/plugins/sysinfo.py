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
System information plugin
"""

from avocado.core import sysinfo
from avocado.core.plugins import plugin


class SystemInformation(plugin.Plugin):

    """
    Collect system information
    """

    name = 'sysinfo'
    enabled = True

    def configure(self, parser):
        """
        Add the subparser for the run action.

        :param parser: Main test runner parser.
        """
        self.parser = parser.subcommands.add_parser(
            'sysinfo',
            help='Collect system information')
        self.parser.add_argument('sysinfodir', type=str,
                                 help='Dir where to dump sysinfo',
                                 nargs='?', default='')
        super(SystemInformation, self).configure(self.parser)

    def run(self, args):
        sysinfo.collect_sysinfo(args)
