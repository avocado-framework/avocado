#!/usr/bin/env python

from avocado import Test
from avocado import main


class NastyException:

    """ Please never use something like this!!! (old-style exception) """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class FailTest(Test):

    """
    This test raises old-style-class exception

    :avocado: tags=failure_expected
    """

    def test(self):
        """
        Avocado should report this as TestError.
        """
        raise NastyException("Nasty-string-like-exception")


if __name__ == "__main__":
    main()
