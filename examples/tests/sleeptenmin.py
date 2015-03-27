#!/usr/bin/python

import os
import time

from avocado import job
from avocado import test


class SleepTenMin(test.Test):

    """
    Sleeps for 10 minutes
    """
    default_params = {'sleep_length': 600,
                      'sleep_cycles': 1,
                      'sleep_method': 'builtin'}

    def runTest(self):
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
            self.report_state()

if __name__ == "__main__":
    job.main()
