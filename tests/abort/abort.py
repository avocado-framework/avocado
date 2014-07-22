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


class abort(test.Test):

    """
    A test that just calls abort() (and abort).
    """

    default_params = {'timeout': 1.0}

    def action(self):
        os.abort()


if __name__ == "__main__":
    job.main()
