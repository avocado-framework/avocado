#!/usr/bin/env python

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

    :avocado: tags=failure_expected
    """

    def test(self):
        """
        Avocado should report this as TestError.
        """
        raise NastyException(None)  # str(Exception) fails!


if __name__ == "__main__":
    main()
