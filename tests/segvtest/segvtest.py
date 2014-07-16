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


class segvtest(test.Test):

    """
    Execute the segv test
    """
    default_params = {'source_file': 'segv.c',
                      'gcc_args': '-g'}

    def setup(self):
        """
        Build the test executable
        """
        self.cwd = os.getcwd()
        self.binary_path = os.path.join(self.srcdir, 'binary')

        source_path = self.get_data_path(self.params.source_file)
        process.system('gcc %s %s -o %s' % (self.params.gcc_args,
                                            source_path,
                                            self.binary_path))


    def action(self):
        """
        Execute test
        """
        process.system(self.binary_path, ignore_status=True)

