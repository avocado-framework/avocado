#!/usr/bin/env python

import time

from avocado import Test
from avocado import main


class TimeoutTest(Test):

    """
    Functional test for avocado. Throw a TestTimeoutError.

    :param sleep_time: How long should the test sleep
    """

    default_params = {'timeout': 3}

    def test(self):
        """
        This should throw a TestTimeoutError.
        """
        sleep_time = self.params.get('sleep_time', default=5)
        self.log.info('Sleeping for %.2f seconds (2 more than the timeout)',
                      sleep_time)
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
