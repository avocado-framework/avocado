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

from .log import configure as configure_log
from .parser import Parser
from .dispatcher import CLIDispatcher
from .dispatcher import CLICmdDispatcher


class AvocadoApp(object):

    """
    Avocado application.
    """

    def __init__(self):

        # Catch all libc runtime errors to STDERR
        os.environ['LIBC_FATAL_STDERR_'] = '1'

        configure_log()
        self.parser = Parser()
        self.cli_dispatcher = CLIDispatcher()
        self.cli_cmd_dispatcher = CLICmdDispatcher()
        self.parser.start()
        self.parser.resume()
        if self.cli_cmd_dispatcher.extensions:
            self.cli_cmd_dispatcher.map_method('configure', self.parser)
        if self.cli_dispatcher.extensions:
            self.cli_dispatcher.map_method('configure', self.parser)
        self.ready = True
        self.parser.finish()
        try:
            if self.cli_dispatcher.extensions:
                self.cli_dispatcher.map_method('run', self.parser.args)
        except IOError:
            self.ready = False

    def run(self):
        if self.ready:
            subcommand = self.parser.args.subcommand
            if subcommand in self.cli_cmd_dispatcher:
                extension = self.cli_cmd_dispatcher[subcommand]
                method = extension.obj.run
                return method(self.parser.args)
