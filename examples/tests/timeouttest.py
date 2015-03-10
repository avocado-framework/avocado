#!/usr/bin/python

import time

import avocado


class TimeoutTest(avocado.Test):

    """
    Functional test for avocado. Throw a TestTimeoutError.
    """
    default_params = {'timeout': 3.0,
                      'sleep_time': 5.0}

    def action(self):
        """
        This should throw a TestTimeoutError.
        """
        self.log.info('Sleeping for %.2f seconds (2 more than the timeout)',
                      self.params.sleep_time)
        time.sleep(self.params.sleep_time)


if __name__ == "__main__":
    avocado.main()
