#!/bin/env python3

import os
import sys

from avocado.core.job import Job
from avocado.core.suite import TestSuite

COMMON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.join(COMMON_DIR, 'tests')

CONFIG = {
    'run.references': [os.path.join(TEST_DIR, 'vmimage.py')],
    'yaml_to_mux.files': [os.path.join(TEST_DIR, 'vmimage.py.data', 'variants.yml')],
    }


if __name__ == '__main__':
    suite = TestSuite.from_config(CONFIG)
    with Job(CONFIG, [suite]) as j:
        sys.exit(j.run())
