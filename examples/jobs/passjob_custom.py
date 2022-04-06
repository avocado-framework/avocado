#!/usr/bin/env python3

import sys

from avocado.core.job import Job
from avocado.core.nrunner.runnable import Runnable
from avocado.core.suite import TestSuite

# Custom method (no discovery, no guess, no magic)
# Since there is no magic, we need to pass a suite name, otherwise a uuid4 will
# be used for suite.name. Also resolver.references will be ignored (Avocado will not
# creating tests suites for you).

suite1 = TestSuite(name='suite1', tests=[Runnable("noop", "noop")])
suite2 = TestSuite(name='suite2', tests=[Runnable("noop", "noop")])
suite3 = TestSuite(name='suite3', enabled=False,
                   tests=[Runnable("noop", "noop")])

with Job(test_suites=[suite1, suite2, suite3]) as j:
    sys.exit(j.run())
