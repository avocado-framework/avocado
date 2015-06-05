#!/usr/bin/python

from avocado import Test
from avocado import main


class NastyException(Exception):

    """ Please never use something like this!!! """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class FailTest(Test):

    """
    Very nasty exception test
    """

    def runTest(self):
        """
        Should fail.
        """
        raise NastyException(None)  # str(Exception) fails!


if __name__ == "__main__":
    main()
