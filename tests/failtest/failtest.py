#!/usr/bin/python

from avocado import test
from avocado import job
from avocado.core import exceptions


class failtest(test.Test):

    """
    Functional test for avocado. Straight up fail the test.
    """

    def action(self, length=1):
        """
        Sleep for length seconds.
        """
        raise exceptions.TestFail('This test is supposed to fail')


if __name__ == "__main__":
    job.main()
