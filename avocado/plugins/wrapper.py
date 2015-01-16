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

from avocado import runtime
from avocado.core import exit_codes
from avocado.core import output
from avocado.plugins import plugin


class Wrapper(plugin.Plugin):

    name = 'wrapper'
    enabled = True

    def configure(self, parser):
        self.parser = parser
        wrap_group = self.parser.runner.add_argument_group(
            'Wrap avocado.utils.process module')
        wrap_group.add_argument('--wrapper', action='append', default=[],
                                help='')
        self.configured = True

    def activate(self, app_args):
        view = output.View(app_args=app_args)
        try:
            for wrap in app_args.wrapper:
                if ':' not in wrap:
                    if runtime.WRAP_PROCESS is None:
                        script = os.path.abspath(wrap)
                        runtime.WRAP_PROCESS = os.path.abspath(script)
                    else:
                        view.notify(event='error',
                                    msg="You can't have multiple global"
                                        " wrappers at once.")
                        sys.exit(exit_codes.AVOCADO_FAIL)
                else:
                    script, cmd = wrap.split(':', 1)
                    script = os.path.abspath(script)
                    runtime.WRAP_PROCESS_NAMES_EXPR.append((script, cmd))
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
