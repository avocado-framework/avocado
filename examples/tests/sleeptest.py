import time

from avocado import Test


class SleepTest(Test):

    """
    This test sleeps for 1s by default

    :param sleep_length: Sleep duration
    """

    def test(self):
        """
        Sleep for length seconds.
        """
        sleep_length = float(self.params.get('sleep_length', default=1))
        self.log.debug("Sleeping for %.2f seconds", sleep_length)
        time.sleep(sleep_length)
