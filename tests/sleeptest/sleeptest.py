#!/usr/bin/python

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
