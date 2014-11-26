#!/usr/bin/python

from avocado import test
from avocado import job
from avocado.core import exceptions


class warntest(test.Test):

    """
    Functional test for avocado. Throw a TestWarn.
    """

    def action(self):
        """
        This should throw a TestWarn.
        """
        raise exceptions.TestWarn('This should throw a TestWarn')

if __name__ == "__main__":
    job.main()
