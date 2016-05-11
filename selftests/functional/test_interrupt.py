import os
import sys
import tempfile
import time
import shutil
import stat

import aexpect
import psutil

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.utils import wait
from avocado.utils import script
from avocado.utils import data_factory


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


# What is commonly known as "0755" or "u=rwx,g=rx,o=rx"
DEFAULT_MODE = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                stat.S_IRGRP | stat.S_IXGRP |
                stat.S_IROTH | stat.S_IXOTH)

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

GOOD_TEST = """#!/usr/bin/env python
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
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def test_badly_behaved(self):
        """
        Make sure avocado can cleanly get out of a loop of badly behaved tests.
        """
        bad_test_basename = ('wontquit-%s' %
                             data_factory.generate_random_string(5))
        bad_test = script.TemporaryScript(bad_test_basename, BAD_TEST,
                                          'avocado_interrupt_test',
                                          mode=DEFAULT_MODE)

        bad_test.save()

        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    '%s %s %s' % (self.tmpdir,
                                  bad_test.path,
                                  bad_test.path,
                                  bad_test.path))
        proc = aexpect.Expect(command=cmd_line, linesep='')
        proc.read_until_last_line_matches(os.path.basename(bad_test.path))
        proc.sendline('\x03')
        proc.read_until_last_line_matches('Interrupt requested. Waiting 2 '
                                          'seconds for test to finish '
                                          '(ignoring new Ctrl+C until then)')
        # We have to actually wait 2 seconds until the ignore window is over
        time.sleep(2)
        proc.sendline('\x03')
        proc.read_until_last_line_matches('TESTS TIME : %d s')
        wait.wait_for(lambda: not proc.is_alive(), timeout=1)

        # Make sure the bad test will be really gone from the process table
        def wait_until_no_badtest():
            bad_test_processes = []

            old_psutil = False
            try:
                process_list = psutil.pids()
            except AttributeError:
                process_list = psutil.get_pid_list()
                old_psutil = True

            for p in process_list:
                try:
                    p_obj = psutil.Process(p)
                    if p_obj is not None:
                        if old_psutil:
                            cmdline_list = psutil.Process(p).cmdline
                        else:
                            cmdline_list = psutil.Process(p).cmdline()
                        if bad_test.path in " ".join(cmdline_list):
                            bad_test_processes.append(p_obj)
                # psutil.NoSuchProcess happens when the original
                # process already ended and left the process table
                except psutil.NoSuchProcess:
                    pass

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
                                           mode=DEFAULT_MODE)
        good_test.save()

        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    '%s %s %s' % (self.tmpdir,
                                  good_test.path,
                                  good_test.path,
                                  good_test.path))
        proc = aexpect.Expect(command=cmd_line, linesep='')
        proc.read_until_last_line_matches(os.path.basename(good_test.path))
        proc.sendline('\x03')
        proc.read_until_last_line_matches('TESTS TIME : %d s')
        wait.wait_for(lambda: not proc.is_alive(), timeout=1)

        # Make sure the good test will be really gone from the process table
        def wait_until_no_goodtest():
            good_test_processes = []

            old_psutil = False
            try:
                process_list = psutil.pids()
            except AttributeError:
                process_list = psutil.get_pid_list()
                old_psutil = True

            for p in process_list:
                try:
                    p_obj = psutil.Process(p)
                    if p_obj is not None:
                        if old_psutil:
                            cmdline_list = psutil.Process(p).cmdline
                        else:
                            cmdline_list = psutil.Process(p).cmdline()
                        if good_test.path in " ".join(cmdline_list):
                            good_test_processes.append(p_obj)
                # psutil.NoSuchProcess happens when the original
                # process already ended and left the process table
                except psutil.NoSuchProcess:
                    pass

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
