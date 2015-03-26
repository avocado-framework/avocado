#!/usr/bin/python

import os
import time

from avocado import job
from avocado import test


class SleepTenMin(test.Test):

    """
    Sleeps for 10 minutes
    """

    def action(self):
        """
        Sleep for length seconds.
        """
        cycles = int(self.params.get('sleep_cycles', 1))
        length = int(self.params.get('sleep_length', 600))
        method = self.params.get('sleep_method', 'builtin')

        for cycle in xrange(0, cycles):
            self.log.debug("Sleeping for %.2f seconds", length)
            if method == 'builtin':
                time.sleep(length)
            elif method == 'shell':
                os.system("sleep %s" % length)
            self.report_state()

if __name__ == "__main__":
    job.main()
