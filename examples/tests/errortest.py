#!/usr/bin/env python

from avocado import Test
from avocado import main


class ErrorTest(Test):

    """
    Example test that ends with ERROR.
    """

    def test(self):
        """
        This should end with ERROR.
        """
        self.error('This should end with ERROR.')

if __name__ == "__main__":
    main()
