#!/bin/env python3

import os
import sys

from avocado.core.job import Job


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELEASE_TESTS_DIR = os.path.join(ROOT_DIR, 'selftests', 'release')

CONFIG = {
    'run.references': [os.path.join(RELEASE_TESTS_DIR, 'vmimage.py')],
    'mux_yaml': [os.path.join(RELEASE_TESTS_DIR, 'vmimage.py.data', 'variants.yml')],
    }


if __name__ == '__main__':
    with Job(CONFIG) as j:
        sys.exit(j.run())
