#!/usr/bin/python

from avocado import Test
from avocado import main


class SkipTest(Test):

    """
    Example test that skips the current test, that is it, ends with SKIP.
    """

    def test(self):
        """
        This should end with SKIP.
        """
        self.skip('This should end with SKIP.')

if __name__ == "__main__":
    main()
