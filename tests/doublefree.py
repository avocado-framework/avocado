#!/usr/bin/python

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

from avocado import test
from avocado import job
from avocado.utils import build
from avocado.utils import process


class doublefree(test.Test):

    """
    Double free test case.
    """

    default_params = {'source': 'doublefree.c'}

    def setup(self):
        """
        Build 'doublefree'.
        """
        self.cwd = os.getcwd()
        c_file = self.get_data_path(self.params.source)
        self.srcdir = os.path.dirname(c_file)
        build.make(self.srcdir, env='CFLAGS="-g -O0"', extra_args='doublefree')

    def action(self):
        """
        Execute 'doublefree'.
        """
        cmd = os.path.join(self.srcdir, 'doublefree')
        cmd_result = process.run(cmd)
        self.log.info(cmd_result)

    def cleanup(self):
        """
        Clean up 'doublefree'.
        """
        os.unlink(os.path.join(self.srcdir, 'doublefree'))

if __name__ == "__main__":
    job.main()
