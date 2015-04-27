#!/usr/bin/python

from avocado import test
from avocado import main
from avocado.core import exceptions


class SkipTest(test.Test):

    """
    Functional test for avocado. Throw a TestNAError (skips the test).
    """

    def runTest(self):
        """
        This should throw a TestNAError (skips the test).
        """
        raise exceptions.TestNAError('This test should be skipped')

if __name__ == "__main__":
    main()
