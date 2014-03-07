import time
from avocado import test


class sleeptest(test.Test):

    """
    Example test for avocado.
    """

    def action(self, length=1):
        """
        Sleep for length seconds.
        """
        time.sleep(length)
