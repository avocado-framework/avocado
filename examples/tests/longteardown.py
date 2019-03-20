#!/usr/bin/env python

import time

from avocado import main
from avocado import Test


class LongTearDown(Test):

    """
    Example test with a longer than usual tearDown()
    """

    timeout = 1.0

    def test(self):
        """
        Should be interrupted because of sleep longer than test timeout
        """
        time.sleep(2)

    def tearDown(self):
        time.sleep(2)
        self.whiteboard = 'TEARDOWN PERFORMED'


if __name__ == "__main__":
    main()
