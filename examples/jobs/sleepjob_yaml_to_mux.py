#!/usr/bin/env python3

import sys

from avocado.core.job import Job
from avocado.core.suite import TestSuite

config = {'resolver.references': ['examples/tests/sleeptest.py:SleepTest.test'],
          'yaml_to_mux.files': ['examples/tests/sleeptest.py.data/sleeptest.yaml']}

suite = TestSuite.from_config(config)
with Job(config, [suite]) as j:
    sys.exit(j.run())
