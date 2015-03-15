#!/usr/bin/python

import avocado

from avocado.core import exceptions


class DoubleFail(avocado.Test):

    """
    Functional test for avocado. Straight up fail the test.
    """

    def action(self):
        """
        Should fail.
        """
        raise exceptions.TestFail('This test is supposed to fail')

    def cleanup(self):
        """
        Should also fail.
        """
        raise exceptions.TestError('Failing during cleanup. Yay!')


if __name__ == "__main__":
    avocado.main()
