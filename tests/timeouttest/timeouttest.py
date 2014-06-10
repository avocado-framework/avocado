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

from avocado import test
from avocado import job


class timeouttest(test.Test):

    """
    Functional test for avocado. Throw a TestTimeoutError.
    """
    default_params = {'timeout': 3.0,
                      'sleep_time': 5.0}

    def action(self):
        """
        This should throw a TestTimeoutError.
        """
        self.log.info('Sleeping for %.2f seconds (2 more than the timeout)',
                      self.params.sleep_time)
        time.sleep(self.params.sleep_time)


if __name__ == "__main__":
    job.main()
