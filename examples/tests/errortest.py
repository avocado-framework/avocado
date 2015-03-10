#!/usr/bin/python

import avocado

from avocado.core import exceptions


class ErrorTest(avocado.Test):

    """
    Functional test for avocado. Throw a TestError.
    """

    def action(self):
        """
        This should throw a TestError.
        """
        raise exceptions.TestError('This should throw a TestError')

if __name__ == "__main__":
    avocado.main()
