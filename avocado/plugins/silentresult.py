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

import json

from avocado.plugins import plugin


class Silent(plugin.Plugin):

    """
    Silent output plugin.
    """

    name = 'silent_output'
    enabled = True

    def configure(self, app_parser, cmd_parser):
        self.parser = app_parser
        self.parser.add_argument('--silent', action='store_true', default=False)
        self.configured = True
