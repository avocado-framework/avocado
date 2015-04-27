#!/usr/bin/python

from avocado import test
from avocado import main


class NastyException(Exception):

    """ Please never use something like this!!! """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class FailTest(test.Test):

    """
    Very nasty exception test
    """

    def runTest(self):
        """
        Should fail not-that-badly
        """
        raise NastyException("Nasty-string-like-exception")


if __name__ == "__main__":
    main()
