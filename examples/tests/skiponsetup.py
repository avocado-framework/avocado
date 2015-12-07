#!/usr/bin/env python

from avocado import Test
from avocado import main


class SkipOnSetupTest(Test):

    """
    Example test that skips the current test, on the setUp phase.
    """

    def setUp(self):
        """
        This should end with SKIP.
        """
        self.skip('This should end with SKIP.')

    def test_wont_be_executed(self):
        """
        This won't get to be executed, given that setUp calls .skip().
        """
        pass

if __name__ == "__main__":
    main()
