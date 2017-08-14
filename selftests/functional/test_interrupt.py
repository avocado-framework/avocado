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


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)

AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD", "./scripts/avocado")


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

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

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
        os.chdir(basedir)
        cmd = ('%s run %s --sysinfo=off --job-results-dir %s ' %
               (AVOCADO, bad_test.path, self.tmpdir))
        proc = subprocess.Popen(cmd.split(),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        def has_children():
            return len(psutil.Process(proc.pid).children()) > 0
        wait.wait_for(has_children, timeout=5)

        os.kill(proc.pid, signal.SIGINT)
        time.sleep(2.5)
        # We have to actually wait 2+ seconds until
        # the ignore window is over
        os.kill(proc.pid, signal.SIGINT)

        def is_finished():
            return proc.poll() is not None
        finished = wait.wait_for(is_finished, timeout=5)
        if not finished:
            process.kill_process_tree(proc.pid)
            self.fail('Avocado was still running after receiving SIGINT '
                      'twice.')

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
                            try:
                                cmdline_list = psutil.Process(p).cmdline()
                            except psutil.AccessDenied:
                                cmdline_list = []
                        if bad_test.path in " ".join(cmdline_list):
                            bad_test_processes.append(p_obj)
                # psutil.NoSuchProcess happens when the original
                # process already ended and left the process table
                except psutil.NoSuchProcess:
                    pass

            return len(bad_test_processes) == 0

        if not wait.wait_for(wait_until_no_badtest, timeout=2):
            self.fail('Avocado left processes behind.')

        output = proc.communicate()[0]
        # Make sure the Interrupted requested sentence is there
        self.assertIn('Interrupt requested. Waiting 2 seconds for test to '
                      'finish (ignoring new Ctrl+C until then)', output)
        # Make sure the Killing test subprocess message did appear
        self.assertIn('Killing test subprocess', output)

    @unittest.skipIf(int(os.environ.get("AVOCADO_CHECK_LEVEL", 0)) < 1,
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

        os.chdir(basedir)
        cmd = ('%s run %s --sysinfo=off --job-results-dir %s ' %
               (AVOCADO, good_test.path, self.tmpdir))
        proc = subprocess.Popen(cmd.split(),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        def has_children():
            return len(psutil.Process(proc.pid).children()) > 0
        wait.wait_for(has_children, timeout=5)

        os.kill(proc.pid, signal.SIGINT)

        def is_finished():
            return proc.poll() is not None
        finished = wait.wait_for(is_finished, timeout=5)
        if not finished:
            process.kill_process_tree(proc.pid)
            self.fail('Avocado was still running after receiving SIGINT.')

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
                            try:
                                cmdline_list = psutil.Process(p).cmdline()
                            except psutil.AccessDenied:
                                cmdline_list = []
                        if good_test.path in " ".join(cmdline_list):
                            good_test_processes.append(p_obj)
                # psutil.NoSuchProcess happens when the original
                # process already ended and left the process table
                except psutil.NoSuchProcess:
                    pass

            return len(good_test_processes) == 0

        if not wait.wait_for(wait_until_no_goodtest, timeout=2):
            self.fail('Avocado left processes behind.')

        output = proc.communicate()[0]
        # Make sure the Killing test subprocess message is not there
        self.assertNotIn('Killing test subprocess', output)
        # Make sure the Interrupted requested sentence is there
        self.assertIn('Interrupt requested. Waiting 2 seconds for test to '
                      'finish (ignoring new Ctrl+C until then)', output)

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
        os.chdir(basedir)
        cmd = ('%s run %s --sysinfo=off --job-results-dir %s ' %
               (AVOCADO, bad_test.path, self.tmpdir))
        proc = subprocess.Popen(cmd.split(),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        def has_children():
            return len(psutil.Process(proc.pid).children()) > 0
        wait.wait_for(has_children, timeout=5)

        os.kill(proc.pid, signal.SIGTERM)

        def is_finished():
            return proc.poll() is not None
        finished = wait.wait_for(is_finished, timeout=5)
        if not finished:
            process.kill_process_tree(proc.pid)
            self.fail('Avocado was still running after receiving SIGINT '
                      'twice.')

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
                            try:
                                cmdline_list = psutil.Process(p).cmdline()
                            except psutil.AccessDenied:
                                cmdline_list = []
                        if bad_test.path in " ".join(cmdline_list):
                            bad_test_processes.append(p_obj)
                # psutil.NoSuchProcess happens when the original
                # process already ended and left the process table
                except psutil.NoSuchProcess:
                    pass

            return len(bad_test_processes) == 0

        if not wait.wait_for(wait_until_no_badtest, timeout=2):
            self.fail('Avocado left processes behind.')

        output = proc.communicate()[1]
        # Make sure the Interrupted test sentence is there
        self.assertIn('Terminated\n', output)

    @unittest.skipIf(int(os.environ.get("AVOCADO_CHECK_LEVEL", 0)) < 1,
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

        os.chdir(basedir)
        cmd = ('%s run %s --sysinfo=off --job-results-dir %s ' %
               (AVOCADO, good_test.path, self.tmpdir))
        proc = subprocess.Popen(cmd.split(),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        def has_children():
            return len(psutil.Process(proc.pid).children()) > 0
        wait.wait_for(has_children, timeout=5)

        os.kill(proc.pid, signal.SIGTERM)

        def is_finished():
            return proc.poll() is not None
        finished = wait.wait_for(is_finished, timeout=5)
        if not finished:
            process.kill_process_tree(proc.pid)
            self.fail('Avocado was still running after receiving SIGINT.')

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
                            try:
                                cmdline_list = psutil.Process(p).cmdline()
                            except psutil.AccessDenied:
                                cmdline_list = []
                        if good_test.path in " ".join(cmdline_list):
                            good_test_processes.append(p_obj)
                # psutil.NoSuchProcess happens when the original
                # process already ended and left the process table
                except psutil.NoSuchProcess:
                    pass

            return len(good_test_processes) == 0

        if not wait.wait_for(wait_until_no_goodtest, timeout=2):
            self.fail('Avocado left processes behind.')

        output = proc.communicate()[1]
        # Make sure the Interrupted test sentence is there
        self.assertIn('Terminated\n', output)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
