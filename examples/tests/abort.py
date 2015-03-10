#!/usr/bin/python

import os

import avocado

class AbortTest(avocado.Test):

    """
    A test that just calls abort() (and abort).
    """
    default_params = {'timeout': 2.0}

    def action(self):
        os.abort()


if __name__ == "__main__":
    avocado.main()
