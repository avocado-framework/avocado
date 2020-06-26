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

import os
import sys

from avocado.core import exit_codes
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLI
from avocado.core.settings import settings
from avocado.utils import process


class Wrapper(CLI):

    """
    Implements the '--wrapper' flag for the 'run' subcommand
    """

    name = 'wrapper'
    description = "Implements the '--wrapper' flag for the 'run' subcommand"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        wrap_group = run_subcommand_parser.add_argument_group(
            'wrapper support')
        help_msg = ('Use a script to wrap executables run by a test. The '
                    'wrapper is either a path to a script (AKA a global '
                    'wrapper) or a path to a script followed by colon symbol '
                    '(:), plus a shell like glob to the target EXECUTABLE. '
                    'Multiple wrapper options are allowed, but only one '
                    'global wrapper can be defined.')
        settings.register_option(section='run.wrapper',
                                 key='wrappers',
                                 default=[],
                                 key_type=list,
                                 help_msg=help_msg,
                                 action='append',
                                 metavar='SCRIPT[:EXECUTABLE]',
                                 parser=wrap_group,
                                 long_arg='--wrapper')

    def run(self, config):
        wraps = config.get('run.wrapper.wrappers')
        if wraps:
            for wrap in wraps:
                if ':' not in wrap:
                    if process.WRAP_PROCESS is None:
                        script = os.path.abspath(wrap)
                        process.WRAP_PROCESS = os.path.abspath(script)
                    else:
                        LOG_UI.error("You can't have multiple global "
                                     "wrappers at once.")
                        sys.exit(exit_codes.AVOCADO_FAIL)
                else:
                    script, cmd = wrap.split(':', 1)
                    script = os.path.abspath(script)
                    process.WRAP_PROCESS_NAMES_EXPR.append((script, cmd))
                if not os.path.exists(script):
                    LOG_UI.error("Wrapper '%s' not found!", script)
                    sys.exit(exit_codes.AVOCADO_FAIL)
