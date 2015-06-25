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

from . import plugin
from .. import exit_codes
from .. import output
from ...utils import process


class Wrapper(plugin.Plugin):

    """
    Implements the '--wrapper' flag for the 'run' subcommand
    """

    name = 'wrapper'
    enabled = True

    def configure(self, parser):
        self.parser = parser
        wrap_group = self.parser.runner.add_argument_group(
            'wrapper support')
        wrap_group.add_argument('--wrapper', action='append', default=[],
                                metavar='SCRIPT[:EXECUTABLE]',
                                help='Use a script to wrap executables run by '
                                'a test. The wrapper is either a path to a '
                                'script (AKA a global wrapper) or '
                                'a path to a script followed by colon symbol (:), '
                                'plus a shell like glob to the target EXECUTABLE. '
                                'Multiple wrapper options are allowed, but '
                                'only one global wrapper can be defined.')
        self.configured = True

    def activate(self, app_args):
        try:
            if not app_args.wrapper:    # Not enabled
                return
            view = output.View(app_args=app_args)
            for wrap in app_args.wrapper:
                if ':' not in wrap:
                    if process.WRAP_PROCESS is None:
                        script = os.path.abspath(wrap)
                        process.WRAP_PROCESS = os.path.abspath(script)
                    else:
                        view.notify(event='error',
                                    msg="You can't have multiple global"
                                        " wrappers at once.")
                        sys.exit(exit_codes.AVOCADO_FAIL)
                else:
                    script, cmd = wrap.split(':', 1)
                    script = os.path.abspath(script)
                    process.WRAP_PROCESS_NAMES_EXPR.append((script, cmd))
                if not os.path.exists(script):
                    view.notify(event='error',
                                msg="Wrapper '%s' not found!" % script)
                    sys.exit(exit_codes.AVOCADO_FAIL)
            if app_args.gdb_run_bin:
                view.notify(event='error',
                            msg='Command line option --wrapper is incompatible'
                                ' with option --gdb-run-bin.')
                sys.exit(exit_codes.AVOCADO_FAIL)
        except AttributeError:
            pass
