import time

from avocado import Test


class TimeoutTest(Test):
    """
    Functional test for avocado. Throw a TestTimeoutError.

    :param sleep_time: How long should the test sleep
    """

    def test(self):
        """
        This should throw a TestTimeoutError.
        """
        with self.wait_max(3):
            sleep_time = float(self.params.get("sleep_time", default=5.0))
            self.log.info(
                "Sleeping for %.2f seconds (2 more than the timeout)", sleep_time
            )
            time.sleep(sleep_time)
