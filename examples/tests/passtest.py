#!/usr/bin/python

from avocado import main
from avocado import Test


class PassTest(Test):

    """
    Example test that passes.
    """

    def runTest(self):
        """
        A test simply doesn't have to fail in order to pass
        """
        pass


if __name__ == "__main__":
    main()
