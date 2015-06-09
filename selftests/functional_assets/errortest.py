#!/usr/bin/python

from avocado import Test
from avocado import main
from avocado.core import exceptions


class ErrorTest(Test):

    """
    Functional test for avocado. Throw a TestError.
    """

    def runTest(self):
        """
        This should throw a TestError.
        """
        raise exceptions.TestError('This should throw a TestError')

if __name__ == "__main__":
    main()
