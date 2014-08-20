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


import os
import time

from avocado import job
from avocado import test


class sleeptenmin(test.Test):

    """
    Sleeps for 10 minutes
    """
    default_params = {'sleep_length': 600,
                      'sleep_cycles': 1,
                      'sleep_method': 'builtin'}

    def action(self):
        """
        Sleep for length seconds.
        """
        cycles = int(self.params.sleep_cycles)
        length = int(self.params.sleep_length)

        for cycle in xrange(0, cycles):
            self.log.debug("Sleeping for %.2f seconds", length)
            if self.params.sleep_method == 'builtin':
                time.sleep(length)
            elif self.params.sleep_method == 'shell':
                os.system("sleep %s" % length)

if __name__ == "__main__":
    job.main()
