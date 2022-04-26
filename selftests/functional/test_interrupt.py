import os
import signal
import stat
import subprocess
import time
import unittest

import psutil

from avocado.utils import data_factory, process, script, wait
from selftests.utils import (AVOCADO, BASEDIR, TestCaseTmpDir,
                             skipOnLevelsInferiorThan)

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
from avocado.core import main

class GoodTest(Test):
    def test(self):
        time.sleep(600)

if __name__ == "__main__":
    main()
"""


class InterruptTest(TestCaseTmpDir):

    @staticmethod
    def has_children(proc):
        return len(psutil.Process(proc.pid).children()) > 0

    @staticmethod
    def is_finished(proc):
        return proc.poll() is not None

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
        super().setUp()
        self.test_module = None

    @unittest.skip('Skip until '
                   'https://github.com/avocado-framework/avocado/issues/4994 '
                   'is implemented')
    @skipOnLevelsInferiorThan(2)
    def test_badly_behaved_sigint(self):
        """
        Make sure avocado can cleanly get out of a loop of badly behaved tests.

        :avocado: tags=parallel:1
        """
        bad_test_basename = \
            f'wontquit-{data_factory.generate_random_string(5)}'
        bad_test = script.TemporaryScript(bad_test_basename, BAD_TEST,
                                          'avocado_interrupt_test',
                                          mode=DEFAULT_MODE)
        bad_test.save()
        self.test_module = bad_test.path
        os.chdir(BASEDIR)
        cmd = (f'{AVOCADO} run {self.test_module} --disable-sysinfo '
               f'--job-results-dir {self.tmpdir.name}')
        proc = subprocess.Popen(cmd.split(),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

        if not wait.wait_for(lambda: self.has_children(proc), timeout=10):
            process.kill_process_tree(proc.pid)
            self.fail('Avocado did not start the test process.')

        # This test will ignore SIGINT, so it should terminate
        # when we send the second SIGINT.
        os.kill(proc.pid, signal.SIGINT)
        # We have to actually wait 2+ seconds until
        # the ignore window is over
        time.sleep(2.5)
        os.kill(proc.pid, signal.SIGINT)

        if not wait.wait_for(lambda: self.is_finished(proc), timeout=30):
            process.kill_process_tree(proc.pid)
            self.fail('Avocado was still running after receiving SIGINT '
                      'twice.')

        self.assertTrue(wait.wait_for(self._no_test_in_process_table,
                                      timeout=10), 'Avocado left processes behind.')

        output = proc.stdout.read()
        # Make sure the Interrupted requested sentence is there
        self.assertIn(b'Interrupt requested. Waiting 2 seconds for test to '
                      b'finish (ignoring new Ctrl+C until then)', output)
        # Make sure the Killing test subprocess message did appear
        self.assertIn(b'Killing test subprocess', output)

    @skipOnLevelsInferiorThan(2)
    def test_badly_behaved_sigterm(self):
        """
        Make sure avocado can cleanly get out of a loop of badly behaved tests.

        :avocado: tags=parallel:1
        """
        bad_test_basename = \
            f'wontquit-{data_factory.generate_random_string(5)}'
        bad_test = script.TemporaryScript(bad_test_basename, BAD_TEST,
                                          'avocado_interrupt_test',
                                          mode=DEFAULT_MODE)
        bad_test.save()
        self.test_module = bad_test.path
        os.chdir(BASEDIR)
        cmd = (f'{AVOCADO} run {self.test_module} --disable-sysinfo '
               f'--job-results-dir {self.tmpdir.name} ')
        proc = subprocess.Popen(cmd.split(),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

        if not wait.wait_for(lambda: self.has_children(proc), timeout=10):
            process.kill_process_tree(proc.pid)
            self.fail('Avocado did not start the test process.')

        # This test should be terminated when the main process
        # receives a SIGTERM, even if the test process ignores SIGTERM.
        os.kill(proc.pid, signal.SIGTERM)

        if not wait.wait_for(lambda: self.is_finished(proc), timeout=10):
            process.kill_process_tree(proc.pid)
            self.fail('Avocado was still running after receiving SIGINT '
                      'twice.')

        self.assertTrue(wait.wait_for(self._no_test_in_process_table,
                                      timeout=10), 'Avocado left processes behind.')

        # Make sure the Interrupted test sentence is there
        self.assertIn(b'Terminated\n', proc.stdout.read())

    @unittest.skip('Skip until '
                   'https://github.com/avocado-framework/avocado/issues/4994 '
                   'is implemented')
    @skipOnLevelsInferiorThan(2)
    def test_well_behaved_sigint(self):
        """
        Make sure avocado can cleanly get out of a loop of well behaved tests.

        :avocado: tags=parallel:1
        """
        good_test_basename = \
            f'goodtest-{data_factory.generate_random_string(5)}.py'
        good_test = script.TemporaryScript(good_test_basename, GOOD_TEST,
                                           'avocado_interrupt_test',
                                           mode=DEFAULT_MODE)
        good_test.save()
        self.test_module = good_test.path
        os.chdir(BASEDIR)
        cmd = (f'{AVOCADO} run {self.test_module} '
               f'--disable-sysinfo --job-results-dir {self.tmpdir.name} ')
        proc = subprocess.Popen(cmd.split(),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

        if not wait.wait_for(lambda: self.has_children(proc), timeout=10):
            process.kill_process_tree(proc.pid)
            self.fail('Avocado did not start the test process.')

        # This test will not ignore SIGINT, so it should
        # terminate right away.
        os.kill(proc.pid, signal.SIGINT)

        if not wait.wait_for(lambda: self.is_finished(proc), timeout=10):
            process.kill_process_tree(proc.pid)
            self.fail('Avocado was still running after receiving SIGINT '
                      'twice.')

        self.assertTrue(wait.wait_for(self._no_test_in_process_table,
                                      timeout=10), 'Avocado left processes behind.')

        output = proc.stdout.read()
        # Make sure the Interrupted requested sentence is there
        self.assertIn(b'Interrupt requested. Waiting 2 seconds for test to '
                      b'finish (ignoring new Ctrl+C until then)', output)
        # Make sure the Killing test subprocess message is not there
        self.assertNotIn(b'Killing test subprocess', output)

    @skipOnLevelsInferiorThan(2)
    def test_well_behaved_sigterm(self):
        """
        Make sure avocado can cleanly get out of a loop of well behaved tests.

        :avocado: tags=parallel:1
        """
        good_test_basename = \
            f'goodtest-{data_factory.generate_random_string(5)}.py'
        good_test = script.TemporaryScript(good_test_basename, GOOD_TEST,
                                           'avocado_interrupt_test',
                                           mode=DEFAULT_MODE)
        good_test.save()
        self.test_module = good_test.path
        os.chdir(BASEDIR)
        cmd = (f'{AVOCADO} run {self.test_module} --disable-sysinfo '
               f'--job-results-dir {self.tmpdir.name} ')
        proc = subprocess.Popen(cmd.split(),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

        if not wait.wait_for(lambda: self.has_children(proc), timeout=10):
            process.kill_process_tree(proc.pid)
            self.fail('Avocado did not start the test process.')

        # This test should be terminated when the main process
        # receives a SIGTERM.
        os.kill(proc.pid, signal.SIGTERM)

        if not wait.wait_for(lambda: self.is_finished(proc), timeout=10):
            process.kill_process_tree(proc.pid)
            self.fail('Avocado was still running after receiving SIGINT '
                      'twice.')

        self.assertTrue(wait.wait_for(self._no_test_in_process_table,
                                      timeout=10), 'Avocado left processes behind.')

        # Make sure the Interrupted test sentence is there
        self.assertIn(b'Terminated\n', proc.stdout.read())


if __name__ == '__main__':
    unittest.main()
