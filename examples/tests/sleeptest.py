#!/usr/bin/env python

import time

from avocado import Test
from avocado import main


class SleepTest(Test):

    """
    This test sleeps for 1s by default

    :param sleep_length: Sleep duration
    """

    def test(self):
        """
        Sleep for length seconds.
        """
        sleep_length = self.params.get('sleep_length', default=1)
        self.log.debug("Sleeping for %.2f seconds", sleep_length)
        time.sleep(sleep_length)


if __name__ == "__main__":
    main()
