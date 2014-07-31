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


import time

from avocado import job
from avocado import test


class sleeptenmin(test.Test):

    """
    Sleeps for 10 minutes
    """
    default_params = {'sleep_length': 600}

    def action(self):
        """
        Sleep for length seconds.
        """
        self.log.debug("Sleeping for %.2f seconds", self.params.sleep_length)
        time.sleep(self.params.sleep_length)


if __name__ == "__main__":
    job.main()
