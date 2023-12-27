#!/bin/env python3

import os
import sys

from avocado.core.job import Job

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(THIS_DIR)))
TESTS_DIR = os.path.join(os.path.dirname(THIS_DIR), "tests")

parallel_1 = {
    "resolver.references": [
        os.path.join("selftests", "unit"),
        os.path.join("selftests", "functional"),
    ],
    "filter.by_tags.tags": ["parallel:1"],
    "run.max_parallel_tasks": 1,
}

vmimage = {
    "resolver.references": [os.path.join(TESTS_DIR, "vmimage.py")],
    "yaml_to_mux.files": [os.path.join(TESTS_DIR, "vmimage.py.data", "variants.yml")],
    "run.max_parallel_tasks": 1,
}

if __name__ == "__main__":
    os.chdir(ROOT_DIR)
    config = {"job.output.testlogs.statuses": ["FAIL", "ERROR", "INTERRUPT"]}
    with Job.from_config(config, [parallel_1, vmimage]) as j:
        os.environ["AVOCADO_CHECK_LEVEL"] = "3"
        sys.exit(j.run())
