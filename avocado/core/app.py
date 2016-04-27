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
import signal

from .parser import Parser
from . import output
from .output import STD_OUTPUT
from .dispatcher import CLIDispatcher
from .dispatcher import CLICmdDispatcher


class AvocadoApp(object):

    """
    Avocado application.
    """

    def __init__(self):

        # Catch all libc runtime errors to STDERR
        os.environ['LIBC_FATAL_STDERR_'] = '1'

        signal.signal(signal.SIGTSTP, signal.SIG_IGN)   # ignore ctrl+z
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
        self.parser = Parser()
        output.early_start()
        initialized = False
        try:
            self.cli_dispatcher = CLIDispatcher()
            self.cli_cmd_dispatcher = CLICmdDispatcher()
            output.log_plugin_failures(self.cli_dispatcher.load_failures +
                                       self.cli_cmd_dispatcher.load_failures)
            self.parser.start()
            if self.cli_cmd_dispatcher.extensions:
                self.cli_cmd_dispatcher.map_method('configure', self.parser)
            if self.cli_dispatcher.extensions:
                self.cli_dispatcher.map_method('configure', self.parser)
            self.parser.finish()
            if self.cli_dispatcher.extensions:
                self.cli_dispatcher.map_method('run', self.parser.args)
            initialized = True
        finally:
            output.reconfigure(self.parser.args)

    def run(self):
        try:
            try:
                subcmd = self.parser.args.subcommand
                extension = self.cli_cmd_dispatcher[subcmd]
            except KeyError:
                return
            method = extension.obj.run
            return method(self.parser.args)
        finally:
            # This makes sure we cleanup the console (stty echo). The only way
            # to avoid cleaning it is to kill the less (paginator) directly
            STD_OUTPUT.close()
