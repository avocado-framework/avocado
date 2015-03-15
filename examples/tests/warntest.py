#!/usr/bin/python

import avocado

from avocado.core import exceptions


class WarnTest(avocado.Test):

    """
    Functional test for avocado. Throw a TestWarn.
    """

    def action(self):
        """
        This should throw a TestWarn.
        """
        self.log.warn("This marks test as WARN")

if __name__ == "__main__":
    avocado.main()
