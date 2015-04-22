#!/usr/bin/python

from avocado import test
from avocado.core import job
from avocado.core import exceptions


class WarnTest(test.Test):

    """
    Functional test for avocado. Throw a TestWarn.
    """

    def runTest(self):
        """
        This should throw a TestWarn.
        """
        self.log.warn("This marks test as WARN")

if __name__ == "__main__":
    job.main()
