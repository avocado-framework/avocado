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
# Copyright: RedHat 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>


import time

from avocado import job
from avocado import test


class sleeptest(test.Test):

    """
    Example test for avocado.
    """

    def action(self, length=1):
        """
        Sleep for length seconds.
        """
        self.log.debug("Sleeping for %d seconds", length)
        time.sleep(length)


if __name__ == "__main__":
    job.main()
