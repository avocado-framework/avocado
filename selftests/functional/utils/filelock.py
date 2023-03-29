import multiprocessing
import random
import sys
import time

from avocado.utils.filelock import FileLock
from avocado.utils.stacktrace import prepare_exc_info
from selftests.utils import TestCaseTmpDir, skipOnLevelsInferiorThan


def file_lock_action(args):
    path, players, max_individual_timeout = args
    max_timeout = max_individual_timeout * players
    with FileLock(path, max_timeout):
        sleeptime = random.random() / 100
        time.sleep(sleeptime)


class FileLockTest(TestCaseTmpDir):
    @skipOnLevelsInferiorThan(3)
    def test_filelock(self):
        """
        :avocado: tags=parallel:1
        """
        # Calculate the timeout
        start = time.monotonic()
        for _ in range(50):
            with FileLock(self.tmpdir.name):
                pass
        timeout = 0.02 + (time.monotonic() - start)
        players = 500
        pool = multiprocessing.Pool(players)
        args = [(self.tmpdir.name, players, timeout)] * players
        try:
            pool.map(file_lock_action, args)
        except Exception:
            msg = "Failed to run FileLock with %s players:\n%s"
            msg %= (players, prepare_exc_info(sys.exc_info()))
            self.fail(msg)
