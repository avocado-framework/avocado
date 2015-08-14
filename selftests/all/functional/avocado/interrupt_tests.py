import os
import sys
import tempfile
import time
import logging
import shutil

import aexpect
import psutil

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                       '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.insert(0, basedir)

from avocado.utils import wait
from avocado.utils import process
from avocado.utils import script
from avocado.utils import data_factory

BAD_TEST = """#!/usr/bin/env python
import signal
import time

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGQUIT, signal.SIG_IGN)
    while True:
        time.sleep(0.1)
"""

GOOD_TEST = """#!/usr/bin/python
import time
from avocado import Test
from avocado import main

class GoodTest(Test):
    def test(self):
        time.sleep(600)

if __name__ == "__main__":
    main()
"""


class InterruptTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_badly_behaved(self):
        """
        Make sure avocado can cleanly get out of a loop of badly behaved tests.
        """
        bad_test_basename = ('wontquit-%s' %
                             data_factory.generate_random_string(5))
        bad_test = script.TemporaryScript(bad_test_basename, BAD_TEST,
                                          'avocado_interrupt_test',
                                          mode=0755)
        bad_test.save()

        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    '%s %s %s' % (self.tmpdir,
                                  bad_test.path,
                                  bad_test.path,
                                  bad_test.path))
        proc = aexpect.Expect(command=cmd_line, linesep='',
                              output_func=logging.critical)
        proc.read_until_last_line_matches(os.path.basename(bad_test.path))
        proc.sendline('\x03')
        proc.read_until_last_line_matches('Interrupt requested. Waiting 2 '
                                          'seconds for test to finish '
                                          '(ignoring new Ctrl+C until then)')
        # We have to actually wait 2 seconds until the ignore window is over
        time.sleep(2)
        proc.sendline('\x03')
        proc.read_until_last_line_matches('TIME       : %d s')
        wait.wait_for(lambda: not proc.is_alive(), timeout=1)

        # Make sure the bad test will be really gone from the process table
        def wait_until_no_badtest():
            bad_test_processes = [psutil.Process(p) for p in psutil.pids()
                                  if bad_test.path in
                                  " ".join(psutil.Process(p).cmdline())]
            return len(bad_test_processes) == 0

        wait.wait_for(wait_until_no_badtest, timeout=2)
        # Make sure the Killing test subprocess message did appear
        self.assertIn('Killing test subprocess', proc.get_output())

    def test_well_behaved(self):
        """
        Make sure avocado can cleanly get out of a loop of well behaved tests.
        """
        good_test_basename = ('goodtest-%s.py' %
                              data_factory.generate_random_string(5))
        good_test = script.TemporaryScript(good_test_basename, GOOD_TEST,
                                           'avocado_interrupt_test',
                                           mode=0755)
        good_test.save()

        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    '%s %s %s' % (self.tmpdir,
                                  good_test.path,
                                  good_test.path,
                                  good_test.path))
        proc = aexpect.Expect(command=cmd_line, linesep='',
                              output_func=logging.critical)
        proc.read_until_last_line_matches(os.path.basename(good_test.path))
        proc.sendline('\x03')
        proc.read_until_last_line_matches('TIME       : %d s')
        wait.wait_for(lambda: not proc.is_alive(), timeout=1)

        # Make sure the good test will be really gone from the process table
        def wait_until_no_goodtest():
            good_test_processes = [psutil.Process(p) for p in psutil.pids()
                                   if good_test.path in
                                   " ".join(psutil.Process(p).cmdline())]
            return len(good_test_processes) == 0

        wait.wait_for(wait_until_no_goodtest, timeout=2)
        # Make sure the Killing test subprocess message is not there
        self.assertNotIn('Killing test subprocess', proc.get_output())
        # Make sure the Interrupted requested sentence is there
        self.assertIn('Interrupt requested. Waiting 2 seconds for test to '
                      'finish (ignoring new Ctrl+C until then)',
                      proc.get_output())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

if __name__ == '__main__':
    unittest.main()
