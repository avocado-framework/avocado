#!/usr/bin/python

import os

from avocado import test
from avocado import job


class AbortTest(test.Test):

    """
    A test that just calls abort() (and abort).
    """
    default_params = {'timeout': 2.0}

    def runTest(self):
        os.abort()


if __name__ == "__main__":
    job.main()
