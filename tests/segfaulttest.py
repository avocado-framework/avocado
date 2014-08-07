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
# Author: Cleber Rosa <cleber@redhat.com>

import os

from avocado import test
from avocado.utils import process


class segfaulttest(test.Test):

    """
    Execute the segv test
    """

    def setup(self):
        """
        Build the test executable
        """
        self.segfault_binary_path = os.path.join(self.outputdir, 'segfault')
        segfault_source_path = self.get_data_path('segfault.c')
        process.system('gcc -g %s -o %s' % (segfault_source_path,
                                            self.segfault_binary_path))

    def action(self):
        """
        Execute test
        """
        process.system(self.segfault_binary_path, ignore_status=True)
