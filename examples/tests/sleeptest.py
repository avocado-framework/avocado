#!/usr/bin/python

import time

from avocado import job
from avocado import test


class SleepTest(test.Test):

    """
    Example test for avocado.
    """
    def action(self):
        """
        Sleep for length seconds.
        """
        duration = self.params.get('/self/*', 'sleep_length', 1)
        self.log.debug("Sleeping for %.2f seconds", duration)
        time.sleep(duration)


if __name__ == "__main__":
    job.main()
