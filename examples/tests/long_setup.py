#!/usr/bin/env python

from time import sleep

from avocado import main
from avocado import Test


class LongSetup(Test):

    """
    Example test for a setUp() method that will fail for a number of times

    The "timeout" will be applicable won't be applicable to the
    setUp() method, which has its own timeout.

    The setup timeout is set to twice the expected amount of time it'll take,
    while it'll take more than twice the test timeout set.
    """

    timeout = 0.2
    setup_timeout = 1

    def setUp(self):
        sleep(0.5)

    def test(self):
        """
        A test simply doesn't have to fail in order to pass
        """


if __name__ == "__main__":
    main()
