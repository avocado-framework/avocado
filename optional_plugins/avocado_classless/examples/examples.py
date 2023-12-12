#! /usr/bin/env avocado-runner-avocado-classless

"""
Example avocado-classless style tests
"""

import sys

from avocado_classless.test import test


@test
def trivial_pass():
    print("Passes, trivially")


@test
def trivial_fail():
    print("Fails, trivially", file=sys.stderr)
    assert False
