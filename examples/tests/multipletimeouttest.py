#!/usr/bin/env python

import time

from avocado import Test
from avocado import main


class MultipleTimeoutTest(Test):

    """
    Demonstrates setting up per test timeouts.

    :param sleep_time: How long should the test sleep
    """

    default_params = {'test_one': {'timeout': 3},
                      'test_two': {'timeout': 4}}

    def test_one(self):
        """
        This should throw a TestTimeoutError.
        """
        sleep_time = self.params.get('test_one').get('sleep_time', 5)
        self.log.info('Sleeping for %.2f seconds (2 more than the timeout)',
                      sleep_time)
        time.sleep(sleep_time)

    def test_two(self):
        """
        This should throw a TestTimeoutError.
        """
        sleep_time = self.params.get('test_two').get('sleep_time', 5)
        self.log.info('Sleeping for %.2f seconds (1 more than the timeout)',
                      sleep_time)
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
