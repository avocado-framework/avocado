#!/usr/bin/env python3

import sys

from avocado.core.job import Job
from avocado.core.suite import TestSuite

ORDERLY_CONFIG = {
    "resolver.references": ["/bin/true", "/bin/true", "/bin/last"],
    "run.max_parallel_tasks": 1,
}

RANDOM_CONFIG = {
    "resolver.references": [
        "/bin/true",
        "/bin/true",
        "/bin/true",
        "/bin/true",
        "/bin/true",
        "/bin/last",
    ],
    "run.shuffle": True,
    "run.max_parallel_tasks": 1,
}

with Job(
    test_suites=[
        TestSuite.from_config(ORDERLY_CONFIG, name="orderly"),
        TestSuite.from_config(RANDOM_CONFIG, name="random"),
    ]
) as j:
    sys.exit(j.run())
