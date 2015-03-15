#!/usr/bin/python

import avocado

from avocado.core import exceptions


class SkipTest(avocado.Test):

    """
    Functional test for avocado. Throw a TestNAError (skips the test).
    """

    def action(self):
        """
        This should throw a TestNAError (skips the test).
        """
        raise exceptions.TestNAError('This test should be skipped')

if __name__ == "__main__":
    avocado.main()
