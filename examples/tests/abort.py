#!/usr/bin/python

import os

from avocado import Test
from avocado import main


class AbortTest(Test):

    """
    A test that just calls abort() (and abort).
    """

    default_params = {'timeout': 2.0}

    def test(self):
        os.abort()


if __name__ == "__main__":
    main()
