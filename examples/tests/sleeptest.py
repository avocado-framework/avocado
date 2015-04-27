#!/usr/bin/python

import time

from avocado import test
from avocado import main


class SleepTest(test.Test):

    """
    Example test for avocado.
    """

    def runTest(self):
        """
        Sleep for length seconds.
        """
        sleep_length = self.params.get('sleep_length', default=1)
        self.log.debug("Sleeping for %.2f seconds", sleep_length)
        time.sleep(sleep_length)


if __name__ == "__main__":
    main()
