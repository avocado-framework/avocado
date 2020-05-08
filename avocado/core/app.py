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
import sys

from . import data_dir
from . import output
from .dispatcher import CLICmdDispatcher
from .dispatcher import CLIDispatcher
from .output import STD_OUTPUT
from .parser import Parser
from .future.settings import settings
from ..utils import process


class AvocadoApp:

    """
    Avocado application.
    """

    def __init__(self):

        # Catch all libc runtime errors to STDERR
        os.environ['LIBC_FATAL_STDERR_'] = '1'

        def sigterm_handler(signum, frame):     # pylint: disable=W0613
            children = process.get_children_pids(os.getpid())
            for child in children:
                process.kill_process_tree(int(child))
            raise SystemExit('Terminated')

        signal.signal(signal.SIGTERM, sigterm_handler)
        if hasattr(signal, 'SIGTSTP'):
            signal.signal(signal.SIGTSTP, signal.SIG_IGN)   # ignore ctrl+z
        self.parser = Parser()
        self.parser.start()
        output.early_start()

        show = getattr(self.parser.args, 'show', None)
        reconfigure_settings = {'core.paginator': 'off',
                                'show': show}
        try:
            self.cli_dispatcher = CLIDispatcher()
            self.cli_cmd_dispatcher = CLICmdDispatcher()
            output.log_plugin_failures(self.cli_dispatcher.load_failures +
                                       self.cli_cmd_dispatcher.load_failures)
            if self.cli_cmd_dispatcher.extensions:
                self.cli_cmd_dispatcher.map_method('configure', self.parser)
            if self.cli_dispatcher.extensions:
                self.cli_dispatcher.map_method('configure', self.parser)
            self.parser.finish()
            settings.merge_with_configs()
            settings.merge_with_arguments(self.parser.config)
            self.parser.config.update(settings.as_dict())
            if self.cli_dispatcher.extensions:
                self.cli_dispatcher.map_method('run', self.parser.config)
        except SystemExit as detail:
            # If someone tries to exit Avocado, we should first close the
            # STD_OUTPUT and only then exit.
            output.reconfigure(reconfigure_settings)
            STD_OUTPUT.close()
            sys.exit(detail.code)
        except:
            # For any other exception we also need to close the STD_OUTPUT.
            output.reconfigure(reconfigure_settings)
            STD_OUTPUT.close()
            raise
        else:
            # In case of no exceptions, we just reconfigure the output.
            output.reconfigure(self.parser.config)

    def run(self):
        try:
            try:
                subcmd = self.parser.config.get('subcommand')
                extension = self.cli_cmd_dispatcher[subcmd]
            except KeyError:
                return
            method = extension.obj.run
            return method(self.parser.config)
        finally:
            # This makes sure we cleanup the console (stty echo). The only way
            # to avoid cleaning it is to kill the less (paginator) directly
            STD_OUTPUT.close()
            # Force-close tmp dir
            data_dir.clean_tmp_files()
