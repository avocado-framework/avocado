#!/usr/bin/python

import os

from avocado import test
from avocado import job


class abort(test.Test):

    """
    A test that just calls abort() (and abort).
    """

    def action(self):
        os.abort()


if __name__ == "__main__":
    job.main()
