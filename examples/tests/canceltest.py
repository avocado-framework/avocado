#!/usr/bin/env python

from avocado import Test
from avocado import main


class CancelTest(Test):

    """
    Example test that cancels the current test from inside the test.
    """

    def test(self):
        self.cancel("This should end with CANCEL.")


if __name__ == "__main__":
    main()
