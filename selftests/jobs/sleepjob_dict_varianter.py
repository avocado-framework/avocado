#!/usr/bin/env python3

import sys
import tempfile

from avocado.core.job import Job
from avocado.core.suite import TestSuite

test_results_dir = tempfile.TemporaryDirectory()

config = {
    "run.results_dir": test_results_dir.name,
    "resolver.references": ["examples/tests/sleeptest.py:SleepTest.test"],
    "run.dict_variants": [{"sleep_length": "0.5"}, {"sleep_length": "1.0"}],
}

suite = TestSuite.from_config(config)
with Job(config, [suite]) as j:
    exit_code = j.run()
    test_results_dir.cleanup()
    sys.exit(exit_code)
