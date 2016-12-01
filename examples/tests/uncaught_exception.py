#!/usr/bin/env python

from avocado import Test
from avocado import main


class ErrorTest(Test):

    """
    Example test that raises generic exception

    :avocado: tags=failure_expected
    """

    def test(self):
        """
        This should end with ERROR.
        """
        raise Exception("This is a generic exception")


if __name__ == "__main__":
    main()
