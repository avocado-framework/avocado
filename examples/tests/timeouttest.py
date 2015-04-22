#!/usr/bin/python

import time

from avocado import test
from avocado.core import job


class TimeoutTest(test.Test):

    """
    Functional test for avocado. Throw a TestTimeoutError.
    """

    default_params = {'timeout': 3}

    def runTest(self):
        """
        This should throw a TestTimeoutError.
        """
        sleep_time = self.params.get('sleep_time', 5)
        self.log.info('Sleeping for %.2f seconds (2 more than the timeout)',
                      sleep_time)
        time.sleep(sleep_time)


if __name__ == "__main__":
    job.main()
