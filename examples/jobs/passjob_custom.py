import sys

from avocado.core.job import Job
from avocado.core.suite import TestSuite

job_config = {'run.test_runner': 'nrunner'}

config1 = {'run.references': ['examples/tests/passtest.py:PassTest.test']}
config2 = {'run.references': ['examples/tests/passtest.py:PassTest.test']}

# Custom method (no discovery, no guess, no magic)
# Since there is no magic, we need to pass a suite name, otherwise a uuid4 will
# be used for suite.name. Also run.references will be ignored (Avocado will not
# creating tests suites for you).

suite1 = TestSuite(config=config1, tests=[], name='suite1')
suite2 = TestSuite(config=config2, tests=[], name='suite2')

with Job(job_config, [suite1, suite2]) as j:
    sys.exit(j.run())
