#!/usr/bin/env python3

import sys

from avocado.core.job import Job
from avocado.core.suite import TestSuite

config = {'resolver.references': ['examples/tests/sleeptest.py:SleepTest.test'],
          'run.dict_variants': [
              {'sleep_length': "0.5"},
              {'sleep_length': "1.0"}
              ]}

suite = TestSuite.from_config(config)
with Job(config, [suite]) as j:
    sys.exit(j.run())
