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
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>


from avocado import test
from avocado import job
from avocado.core import exceptions


class warntest(test.Test):

    """
    Functional test for avocado. Throw a TestWarn.
    """

    def action(self):
        """
        This should throw a TestWarn.
        """
        raise exceptions.TestWarn('This should throw a TestWarn')

if __name__ == "__main__":
    job.main()
