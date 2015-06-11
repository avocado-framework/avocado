#!/usr/bin/python

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

if __name__ == "__main__":
    main()
