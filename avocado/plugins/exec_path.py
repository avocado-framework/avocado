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
# Copyright: Red Hat Inc. 2013-2015
"""
Libexec PATHs modifier
"""

import os
import sys

from avocado.core import exit_codes
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd


class ExecPath(CLICmd):

    """
    Implements the avocado 'exec-path' subcommand
    """

    name = 'exec-path'
    description = 'Returns path to avocado bash libraries and exits.'

    def run(self, args):
        """
        Print libexec path and finish

        :param args: Command line args received from the run subparser.
        """
        if 'VIRTUAL_ENV' in os.environ:
            LOG_UI.debug('libexec')
        elif os.path.exists('/usr/libexec/avocado'):
            LOG_UI.debug('/usr/libexec/avocado')
        elif os.path.exists('/usr/lib/avocado'):
            LOG_UI.debug('/usr/lib/avocado')
        else:
            for path in os.environ.get('PATH').split(':'):
                if (os.path.exists(os.path.join(path, 'avocado')) and
                    os.path.exists(os.path.join(os.path.dirname(path),
                                                'libexec'))):
                    LOG_UI.debug(os.path.join(os.path.dirname(path), 'libexec'))
                    break
            else:
                LOG_UI.error("Can't locate avocado libexec path")
                sys.exit(exit_codes.AVOCADO_FAIL)
        return sys.exit(exit_codes.AVOCADO_ALL_OK)
