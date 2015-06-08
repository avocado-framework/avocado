#!/usr/bin/python

from avocado import Test
from avocado import main
from avocado.core import exceptions


class FailTest(Test):

    """
    Functional test for avocado. Straight up fail the test.
    """

    def runTest(self):
        """
        Should fail.
        """
        raise exceptions.TestFail('This test is supposed to fail')


if __name__ == "__main__":
    main()
