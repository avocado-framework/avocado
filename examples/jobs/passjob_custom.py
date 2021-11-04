#!/usr/bin/env python3

import sys

from avocado.core.job import Job
from avocado.core.nrunner import Runnable
from avocado.core.suite import TestSuite

# Custom method (no discovery, no guess, no magic)
# Since there is no magic, we need to pass a suite name, otherwise a uuid4 will
# be used for suite.name. Also resolver.references will be ignored (Avocado will not
# creating tests suites for you).

suite1 = TestSuite(config={},
                   tests=[Runnable("noop", "noop")], name='suite1')
suite2 = TestSuite(config={},
                   tests=[Runnable("noop", "noop")], name='suite2')

with Job({}, [suite1, suite2]) as j:
    sys.exit(j.run())
