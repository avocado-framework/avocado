#!/usr/bin/env python3

import sys

from avocado.core.job import Job

config = {'run.references': ['examples/tests/sleeptest.py:SleepTest.test'],
          'run.dict_variants': [
              {'sleep_length': "0.5"},
              {'sleep_length': "1.0"}
              ]}

with Job(config) as j:
    sys.exit(j.run())
