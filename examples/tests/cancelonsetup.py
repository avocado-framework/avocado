#!/usr/bin/env python

from avocado import Test
from avocado import main


class CancelOnSetupTest(Test):

    """
    Example test that cancels the current test, on the setUp phase.
    """

    def setUp(self):
        self.cancel('This should end with CANCEL.')

    def test_wont_be_executed(self):
        """
        This won't get to be executed, given that setUp calls .cancel().
        """


if __name__ == "__main__":
    main()
