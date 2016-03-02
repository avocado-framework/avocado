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
from .settings import settings
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
        self.parser = Parser()
        output.early_start()
        initialized = False
        try:
            self.cli_dispatcher = CLIDispatcher()
            self.cli_cmd_dispatcher = CLICmdDispatcher()
            self._print_plugin_failures()
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
            if (not initialized and
                    getattr(self.parser.args, "silent", False) is False):
                output.enable_stderr()
                self.parser.args.show = ["app"]
            output.reconfigure(self.parser.args)

    def _print_plugin_failures(self):
        failures = (self.cli_dispatcher.load_failures +
                    self.cli_cmd_dispatcher.load_failures)
        if failures:
            view = output.View(self.parser.args)
            msg_fmt = 'Failed to load plugin from module "%s": %s'
            silenced = settings.get_value('plugins',
                                          'skip_broken_plugin_notification',
                                          list, [])
            for failure in failures:
                if failure[0].module_name in silenced:
                    continue
                msg = msg_fmt % (failure[0].module_name,
                                 failure[1].__repr__())
                view.notify(event='error', msg=msg)

    def run(self):
        try:
            extension = self.cli_cmd_dispatcher[self.parser.args.subcommand]
        except KeyError:
            return
        method = extension.obj.run
        return method(self.parser.args)
