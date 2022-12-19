#!/usr/bin/env python3

import sys

from avocado.core.job import Job
from avocado.core.suite import TestSuite

PROCESS_CONFIG = {"resolver.references": ["/bin/true"], "run.spawner": "process"}

PODMAN_CONFIG = {"resolver.references": ["/bin/true"], "run.spawner": "podman"}

with Job(
    test_suites=[
        TestSuite.from_config(PROCESS_CONFIG, name="process"),
        TestSuite.from_config(PODMAN_CONFIG, name="podman"),
    ]
) as j:
    sys.exit(j.run())
