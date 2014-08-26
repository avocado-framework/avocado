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
# Copyright: Red Hat Inc. 2014
# Author: Ruda Moura <rmoura@redhat.com>

"""
Silent output module.
"""

from avocado.plugins import plugin


class Silent(plugin.Plugin):

    """
    Silent output plugin.
    """

    name = 'silent_output'
    enabled = True

    def configure(self, parser):
        self.parser = parser.application.add_argument(
            '--silent', action='store_true', default=False,
            help='Silent output, do not display results.')
        self.configured = True
