import multiprocessing
import os
import random
import shutil
import stat
import sys
import tempfile
import time

from avocado.utils.filelock import FileLock
from avocado.utils.stacktrace import prepare_exc_info


if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.utils import process


# What is commonly known as "0775" or "u=rwx,g=rwx,o=rx"
DEFAULT_MODE = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP |
                stat.S_IROTH | stat.S_IXOTH)

FAKE_VMSTAT_CONTENTS = """#!/usr/bin/env python
import time
import random
import signal
import sys

class FakeVMStat(object):
    def __init__(self, interval):
        self.interval = interval
        self._sysrand = random.SystemRandom()
        def interrupt_handler(signum, frame):
            sys.exit(0)
        signal.signal(signal.SIGINT, interrupt_handler)
        signal.signal(signal.SIGTERM, interrupt_handler)

    def get_r(self):
        return self._sysrand.randint(0, 2)

    def get_b(self):
        return 0

    def get_swpd(self):
        return 0

    def get_free(self):
        return self._sysrand.randint(1500000, 1600000)

    def get_buff(self):
        return self._sysrand.randint(290000, 300000)

    def get_cache(self):
        return self._sysrand.randint(2900000, 3000000)

    def get_si(self):
        return 0

    def get_so(self):
        return 0

    def get_bi(self):
        return self._sysrand.randint(0, 50)

    def get_bo(self):
        return self._sysrand.randint(0, 500)

    def get_in(self):
        return self._sysrand.randint(200, 3000)

    def get_cs(self):
        return self._sysrand.randint(1000, 4000)

    def get_us(self):
        return self._sysrand.randint(0, 40)

    def get_sy(self):
        return self._sysrand.randint(1, 5)

    def get_id(self):
        return self._sysrand.randint(50, 100)

    def get_wa(self):
        return 0

    def get_st(self):
        return 0

    def start(self):
        print("procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----")
        print(" r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st")
        while True:
            r = self.get_r()
            b = self.get_b()
            swpd = self.get_swpd()
            free = self.get_free()
            buff = self.get_buff()
            cache = self.get_cache()
            si = self.get_si()
            so = self.get_so()
            bi = self.get_bi()
            bo = self.get_bo()
            m_in = self.get_in()
            cs = self.get_cs()
            us = self.get_us()
            sy = self.get_sy()
            m_id = self.get_id()
            wa = self.get_wa()
            st = self.get_st()
            print("%2d %2d  %2d   %7d %6d %7d    %1d    %1d    %2d  %3d %4d %2d %2d %1d  %3d  %1d  %1d" %
                  (r, b, swpd, free, buff, cache, si, so, bi, bo, m_in, cs,
                   us, sy, m_id, wa, st))
            time.sleep(self.interval)

if __name__ == '__main__':
    vmstat = FakeVMStat(interval=float(sys.argv[1]))
    vmstat.start()
"""

FAKE_UPTIME_CONTENTS = """#!/usr/bin/env python
if __name__ == '__main__':
    print("17:56:34 up  8:06,  7 users,  load average: 0.26, 0.20, 0.21")

"""


class ProcessTest(unittest.TestCase):

    def setUp(self):
        self.base_logdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.fake_vmstat = os.path.join(self.base_logdir, 'vmstat')
        with open(self.fake_vmstat, 'w') as fake_vmstat_obj:
            fake_vmstat_obj.write(FAKE_VMSTAT_CONTENTS)
        os.chmod(self.fake_vmstat, DEFAULT_MODE)

        self.fake_uptime = os.path.join(self.base_logdir, 'uptime')
        with open(self.fake_uptime, 'w') as fake_uptime_obj:
            fake_uptime_obj.write(FAKE_UPTIME_CONTENTS)
        os.chmod(self.fake_uptime, DEFAULT_MODE)

    def test_process_start(self):
        proc = process.SubProcess('%s 1' % self.fake_vmstat)
        proc.start()
        time.sleep(3)
        proc.terminate()
        proc.wait()
        stdout = proc.get_stdout()
        self.assertIn('memory', stdout, 'result: %s' % stdout)
        self.assertRegexpMatches(stdout, '[0-9]+')

    def test_process_run(self):
        proc = process.SubProcess(self.fake_uptime)
        result = proc.run()
        self.assertEqual(result.exit_status, 0, 'result: %s' % result)
        self.assertIn('load average', result.stdout)

    def tearDown(self):
        shutil.rmtree(self.base_logdir)


def file_lock_action(args):
    path, players = args
    max_individual_timeout = 0.021
    max_timeout = max_individual_timeout * players
    with FileLock(path, max_timeout):
        sleeptime = random.random() / 100
        time.sleep(sleeptime)


class FileLockTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    @unittest.skipIf(os.environ.get("AVOCADO_CHECK_LONG") != "1",
                     "Skipping test that takes a long time to run")
    def test_filelock(self):
        players = 1000
        pool = multiprocessing.Pool(players)
        args = [(self.tmpdir, players)] * players
        try:
            pool.map(file_lock_action, args)
        except:
            msg = 'Failed to run FileLock with %s players:\n%s'
            msg %= (players, prepare_exc_info(sys.exc_info()))
            self.fail(msg)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
