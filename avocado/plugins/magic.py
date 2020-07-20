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
# Copyright: Red Hat Inc. 2020
# Author: Cleber Rosa <crosa@redhat.com>
"""
Outputs the Avocado magic string
"""

from avocado.core.magic import MAGIC
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd


class Magic(CLICmd):

    """
    Outputs the Avocado magic string
    """

    name = 'magic'
    description = 'Outputs the Avocado magic string'

    def run(self, config):
        LOG_UI.info(MAGIC)
