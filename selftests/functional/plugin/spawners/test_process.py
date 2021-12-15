import json
import os

from avocado.utils import process, script
from selftests.utils import AVOCADO, TestCaseTmpDir

TEST_LOGDIR = """from avocado import Test


class LogdirTest(Test):

    def test(self):
        self.log.debug("logdir is: %s" % self.logdir)
"""


class ProcessSpawnerTest(TestCaseTmpDir):

    def test_logdir_path(self):
        test = script.Script(os.path.join(self.tmpdir.name, "logdir_test.py"),
                             TEST_LOGDIR)
        test.save()
        result = process.run("%s run --job-results-dir %s --disable-sysinfo "
                             "--json - -- %s" % (AVOCADO, self.tmpdir.name,
                                                 test))
        res = json.loads(result.stdout_text)
        logfile = res["tests"][0]["logfile"]
        testdir = res["tests"][0]["logdir"]
        with open(logfile, 'r') as debug_file:
            expected = "logdir is: %s" % testdir
            self.assertIn(expected, debug_file.read())
