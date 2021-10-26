#!/usr/bin/env python3

import sys

from avocado import Test
from avocado.core.job import Job

# When using __file__, you need to protect Job.run() within a
# conditional block so that it doesn't get executed *again* and
# generates a loop when loading this file at test execution time.
config = {'resolver.references': [__file__]}


class PassTest(Test):
    def test(self):
        pass


if __name__ == '__main__':
    with Job.from_config(job_config=config) as j:
        sys.exit(j.run())
