#!/usr/bin/env python

from avocado import Test
from avocado import main


class DoubleFail(Test):

    """
    Functional test for avocado. Straight up fail the test.
    """

    def test(self):
        """
        Should fail.
        """
        raise self.fail('This test is supposed to fail')

    def tearDown(self):
        """
        Should also fail.
        """
        raise self.error('Failing during tearDown. Yay!')


if __name__ == "__main__":
    main()
