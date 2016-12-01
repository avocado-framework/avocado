#!/usr/bin/env python

from avocado import Test
from avocado import main


class FailTest(Test):

    """
    Example test for avocado. Straight up fail the test.

    :avocado: tags=failure_expected
    """

    def test(self):
        """
        Should fail.
        """
        self.fail('This test is supposed to fail')


if __name__ == "__main__":
    main()
