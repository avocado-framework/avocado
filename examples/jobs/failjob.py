#!/usr/bin/env python3

import sys

from avocado.core.job import Job

config = {'resolver.references': ['examples/tests/failtest.py:FailTest.test']}

with Job(config) as j:
    sys.exit(j.run())
