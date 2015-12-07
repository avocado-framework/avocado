#!/usr/bin/env python

from avocado import Test
from avocado import main


class WarnTest(Test):

    """
    Functional test for avocado. Throw a TestWarn.
    """

    def test(self):
        """
        This should throw a TestWarn.
        """
        self.log.warn("This marks test as WARN")

if __name__ == "__main__":
    main()
