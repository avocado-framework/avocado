#!/usr/bin/env python3

import sys

from avocado.core.job import Job
from avocado.core.suite import TestSuite

config = {'run.references': ['examples/tests/sleeptest.py:SleepTest.test'],
          'json.variants.load': 'examples/tests/sleeptest.py.data/sleeptest.json'}

suite = TestSuite.from_config(config)
with Job(config, [suite]) as j:
    sys.exit(j.run())
