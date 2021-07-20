import os

from avocado.utils import process
from selftests.utils import AVOCADO, BASEDIR, TestCaseTmpDir


class Coroutine(TestCaseTmpDir):

    def test(self):
        test_path = os.path.join(BASEDIR,
                                 "examples", "tests", "sleeptest_async.py")
        os.environ['PYTHONASYNCIODEBUG'] = '1'
        cmd = ("{} --show=test run --disable-sysinfo --job-results-dir {} "
               "-p sleep_length=0 {}").format(AVOCADO, self.tmpdir.name,
                                              test_path)
        result = process.run(cmd, ignore_status=True)
        self.assertEqual(result.exit_status, 0)
        self.assertNotIn("RuntimeWarning: coroutine 'AsyncSleepTest.test' "
                         "was never awaited", result.stdout_text)
