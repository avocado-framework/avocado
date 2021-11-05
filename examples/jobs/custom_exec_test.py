#!/usr/bin/env python3

import sys

from avocado.core.job import Job
from avocado.core.nrunner import Runnable
from avocado.core.suite import TestSuite

# an exec-test runnable consists of a runnable type (exec-test),
# an uri (examples/tests/sleeptest.sh), followed by zero to n arguments
# ending with zero to m keyword arguments.
#
# During the execution, arguments are appended to the uri and keyword
# arguments are converted to environment variable.

# here, SLEEP_LENGTH become an environment variable
sleeptest = Runnable('exec-test', 'examples/tests/sleeptest.sh',
                     SLEEP_LENGTH='2')
# here, 'Hello World!' is appended to the uri (/usr/bin/echo)
echo = Runnable('exec-test', '/usr/bin/echo', 'Hello World!')

# the execution of examples/tests/sleeptest.sh takes around 2 seconds
# and the output of the /usr/bin/echo test is available at the
# job-results/latest/test-results/exec-test-2-_usr_bin_echo/stdout file.
suite = TestSuite(name="exec-test", tests=[sleeptest, echo])

with Job(test_suites=[suite]) as j:
    sys.exit(j.run())
