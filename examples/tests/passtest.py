#!/usr/bin/python

from avocado import job
from avocado import test


class PassTest(test.Test):

    """
    Example test that passes.
    """

    def runTest(self):
        """
        A test simply doesn't have to fail in order to pass
        """
        pass


if __name__ == "__main__":
    job.main()
