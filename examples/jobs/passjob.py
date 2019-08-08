#!/usr/bin/env python3

import sys
from avocado.core.job import Job

config = {'references': ['examples/tests/passtest.py:PassTest.test']}

with Job(config) as j:
    sys.exit(j.run())
