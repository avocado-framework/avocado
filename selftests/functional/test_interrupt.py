import os
import tempfile
import time
import signal
import shutil
import stat
import subprocess
import unittest

import psutil

from avocado.utils import process
from avocado.utils import wait
from avocado.utils import script
from avocado.utils import data_factory

from .. import AVOCADO, BASEDIR

# What is commonly known as "0755" or "u=rwx,g=rx,o=rx"
DEFAULT_MODE = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                stat.S_IRGRP | stat.S_IXGRP |
                stat.S_IROTH | stat.S_IXOTH)

BAD_TEST = """#!/usr/bin/env python
import multiprocessing
import signal
import time

def foo():
    while True:
        time.sleep(0.1)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGQUIT, signal.SIG_IGN)
    proc = multiprocessing.Process(target=foo)
    proc.start()
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

    def _has_children(self):
        return len(psutil.Process(self.proc.pid).children()) > 0

    def _is_finished(self):
        return self.proc.poll() is not None

    def _no_test_in_process_table(self):
        """
        Make sure the test will be really gone from the
        process table.
        """
        test_processes = []

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
                        try:
                            cmdline_list = psutil.Process(p).cmdline()
                        except psutil.AccessDenied:
                            cmdline_list = []
                    if self.test_module in " ".join(cmdline_list):
                        test_processes.append(p_obj)
            # psutil.NoSuchProcess happens when the original
            # process already ended and left the process table
            except psutil.NoSuchProcess:
                pass

        return len(test_processes) == 0

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.test_module = None

    @unittest.skipIf(int(os.environ.get("AVOCADO_CHECK_LEVEL", 0)) < 2,
                     "Skipping test that take a long time to run, are "
                     "resource intensive or time sensitve")
    def test_badly_behaved_sigint(self):
        """
        Make sure avocado can cleanly get out of a loop of badly behaved tests.
        """
        bad_test_basename = ('wontquit-%s' %
                             data_factory.generate_random_string(5))
        bad_test = script.TemporaryScript(bad_test_basename, BAD_TEST,
                                          'avocado_interrupt_test',
                                          mode=DEFAULT_MODE)
        bad_test.save()
        self.test_module = bad_test.path
        os.chdir(BASEDIR)
        cmd = ('%s run %s --sysinfo=off --job-results-dir %s ' %
               (AVOCADO, self.test_module, self.tmpdir))
        self.proc = subprocess.Popen(cmd.split(),
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)

        if not wait.wait_for(self._has_children, timeout=10):
            process.kill_process_tree(self.proc.pid)
            self.fail('Avocado did not start the test process.')

        # This test will ignore SIGINT, so it should terminate
        # when we send the second SIGINT.
        os.kill(self.proc.pid, signal.SIGINT)
        # We have to actually wait 2+ seconds until
        # the ignore window is over
        time.sleep(2.5)
        os.kill(self.proc.pid, signal.SIGINT)

        if not wait.wait_for(self._is_finished, timeout=10):
            process.kill_process_tree(self.proc.pid)
            self.fail('Avocado was still running after receiving SIGINT '
                      'twice.')

        self.assertTrue(wait.wait_for(self._no_test_in_process_table,
                        timeout=10), 'Avocado left processes behind.')

        output = self.proc.stdout.read()
        # Make sure the Interrupted requested sentence is there
        self.assertIn(b'Interrupt requested. Waiting 2 seconds for test to '
                      b'finish (ignoring new Ctrl+C until then)', output)
        # Make sure the Killing test subprocess message did appear
        self.assertIn(b'Killing test subprocess', output)

    @unittest.skipIf(int(os.environ.get("AVOCADO_CHECK_LEVEL", 0)) < 2,
                     "Skipping test that take a long time to run, are "
                     "resource intensive or time sensitve")
    def test_badly_behaved_sigterm(self):
        """
        Make sure avocado can cleanly get out of a loop of badly behaved tests.
        """
        bad_test_basename = ('wontquit-%s' %
                             data_factory.generate_random_string(5))
        bad_test = script.TemporaryScript(bad_test_basename, BAD_TEST,
                                          'avocado_interrupt_test',
                                          mode=DEFAULT_MODE)
        bad_test.save()
        self.test_module = bad_test.path
        os.chdir(BASEDIR)
        cmd = ('%s run %s --sysinfo=off --job-results-dir %s ' %
               (AVOCADO, self.test_module, self.tmpdir))
        self.proc = subprocess.Popen(cmd.split(),
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)

        if not wait.wait_for(self._has_children, timeout=10):
            process.kill_process_tree(self.proc.pid)
            self.fail('Avocado did not start the test process.')

        # This test should be terminated when the main process
        # receives a SIGTERM, even if the test process ignores SIGTERM.
        os.kill(self.proc.pid, signal.SIGTERM)

        if not wait.wait_for(self._is_finished, timeout=10):
            process.kill_process_tree(self.proc.pid)
            self.fail('Avocado was still running after receiving SIGINT '
                      'twice.')

        self.assertTrue(wait.wait_for(self._no_test_in_process_table,
                        timeout=10), 'Avocado left processes behind.')

        # Make sure the Interrupted test sentence is there
        self.assertIn(b'Terminated\n', self.proc.stdout.read())

    @unittest.skipIf(int(os.environ.get("AVOCADO_CHECK_LEVEL", 0)) < 2,
                     "Skipping test that take a long time to run, are "
                     "resource intensive or time sensitve")
    def test_well_behaved_sigint(self):
        """
        Make sure avocado can cleanly get out of a loop of well behaved tests.
        """
        good_test_basename = ('goodtest-%s.py' %
                              data_factory.generate_random_string(5))
        good_test = script.TemporaryScript(good_test_basename, GOOD_TEST,
                                           'avocado_interrupt_test',
                                           mode=DEFAULT_MODE)
        good_test.save()
        self.test_module = good_test.path
        os.chdir(BASEDIR)
        cmd = ('%s run %s --sysinfo=off --job-results-dir %s ' %
               (AVOCADO, self.test_module, self.tmpdir))
        self.proc = subprocess.Popen(cmd.split(),
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)

        if not wait.wait_for(self._has_children, timeout=10):
            process.kill_process_tree(self.proc.pid)
            self.fail('Avocado did not start the test process.')

        # This test will not ignore SIGINT, so it should
        # terminate right away.
        os.kill(self.proc.pid, signal.SIGINT)

        if not wait.wait_for(self._is_finished, timeout=10):
            process.kill_process_tree(self.proc.pid)
            self.fail('Avocado was still running after receiving SIGINT '
                      'twice.')

        self.assertTrue(wait.wait_for(self._no_test_in_process_table,
                        timeout=10), 'Avocado left processes behind.')

        output = self.proc.stdout.read()
        # Make sure the Interrupted requested sentence is there
        self.assertIn(b'Interrupt requested. Waiting 2 seconds for test to '
                      b'finish (ignoring new Ctrl+C until then)', output)
        # Make sure the Killing test subprocess message is not there
        self.assertNotIn(b'Killing test subprocess', output)

    @unittest.skipIf(int(os.environ.get("AVOCADO_CHECK_LEVEL", 0)) < 2,
                     "Skipping test that take a long time to run, are "
                     "resource intensive or time sensitve")
    def test_well_behaved_sigterm(self):
        """
        Make sure avocado can cleanly get out of a loop of well behaved tests.
        """
        good_test_basename = ('goodtest-%s.py' %
                              data_factory.generate_random_string(5))
        good_test = script.TemporaryScript(good_test_basename, GOOD_TEST,
                                           'avocado_interrupt_test',
                                           mode=DEFAULT_MODE)
        good_test.save()
        self.test_module = good_test.path
        os.chdir(BASEDIR)
        cmd = ('%s run %s --sysinfo=off --job-results-dir %s ' %
               (AVOCADO, self.test_module, self.tmpdir))
        self.proc = subprocess.Popen(cmd.split(),
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)

        if not wait.wait_for(self._has_children, timeout=10):
            process.kill_process_tree(self.proc.pid)
            self.fail('Avocado did not start the test process.')

        # This test should be terminated when the main process
        # receives a SIGTERM.
        os.kill(self.proc.pid, signal.SIGTERM)

        if not wait.wait_for(self._is_finished, timeout=10):
            process.kill_process_tree(self.proc.pid)
            self.fail('Avocado was still running after receiving SIGINT '
                      'twice.')

        self.assertTrue(wait.wait_for(self._no_test_in_process_table,
                        timeout=10), 'Avocado left processes behind.')

        # Make sure the Interrupted test sentence is there
        self.assertIn(b'Terminated\n', self.proc.stdout.read())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
