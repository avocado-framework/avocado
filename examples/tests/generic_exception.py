#!/usr/bin/python

from avocado import Test
from avocado import main


class ErrorTest(Test):

    """
    Example test that raises generic exception
    """

    def runTest(self):
        """
        This should end with ERROR (on default config)
        """
        raise Exception("This is a generic exception")

if __name__ == "__main__":
    main()
