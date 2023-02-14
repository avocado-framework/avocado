import sys

from avocado.core.job import Job
from avocado.core.nrunner.runnable import Runnable
from avocado.core.suite import TestSuite

config = {}

test = Runnable(
    "avocado-instrumented",
    "examples/tests/sleeptest.py:SleepTest.test",
    variant={
        "paths": ["/"],
        "variant_id": None,
        "variant": [["/", [["/", "sleep_length", "0.01"]]]],
    },
)
suite = TestSuite("suite_1", tests=[test])

with Job(config, [suite]) as j:
    sys.exit(j.run())
