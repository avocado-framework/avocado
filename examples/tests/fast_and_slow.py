import time

from avocado import Test


class FastTest(Test):

    """
    Fastest possible test

    :avocado: tags=fast,network
    """

    def test(self):
        pass


class SlowTest(Test):

    """
    Slow test

    :avocado: tags=slow,disk,unsafe
    """
    def test(self):
        time.sleep(3)
