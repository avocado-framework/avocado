#!/usr/bin/python

import time

from avocado import job
from avocado import test


class SleepTest(test.Test):

    """
    Example test for avocado.
    """
    default_params = {'sleep_length': 1.0}

    def runTest(self):
        """
        Sleep for length seconds.
        """
        self.log.debug("Sleeping for %.2f seconds", self.params.sleep_length)
        time.sleep(self.params.sleep_length)


if __name__ == "__main__":
    job.main()
