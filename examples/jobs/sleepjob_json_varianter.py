#!/usr/bin/env python3

import sys

from avocado.core.job import Job

config = {'run.references': ['examples/tests/sleeptest.py:SleepTest.test'],
          'json.variants.load': 'examples/tests/sleeptest.py.data/sleeptest.json'}

with Job(config) as j:
    sys.exit(j.run())
