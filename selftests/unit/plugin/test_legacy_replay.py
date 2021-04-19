import os
import tempfile
import unittest

from avocado.core import test
from avocado.plugins.legacy import replay as replay_legacy
from selftests.utils import setup_avocado_loggers, temp_dir_prefix

setup_avocado_loggers()


class Replay(unittest.TestCase):

    """
    avocado.plugins.Replay unittests
    """

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_replay_map_interrupted_json(self):
        """
        Make sure unexecuted tests are appended
        """
        with open(os.path.join(self.tmpdir.name, "results.json"), "w") as res:
            res.write('{"skip": 3, "tests": [{"test": "executed", "status":'
                      '"PASS"}], "total": 4}')
        rep = replay_legacy.Replay()
        act = rep._create_replay_map(self.tmpdir.name, ["PASS"])
        exp = [None, test.ReplaySkipTest, test.ReplaySkipTest,
               test.ReplaySkipTest]
        self.assertEqual(act, exp)
        act = rep._create_replay_map(self.tmpdir.name, ["INTERRUPTED"])
        exp = [test.ReplaySkipTest, None, None, None]
        self.assertEqual(act, exp)

    def test_replay_map_after_crash(self):
        """
        Tests the fallback to TAP as the source of executed tests when
        JSON was not generated
        """
        with open(os.path.join(self.tmpdir.name, "results.tap"), "w") as res:
            res.write("\n# 1..10\nok 3 test3\nnot ok 2 test2\n1..5")
        rep = replay_legacy.Replay()
        act = rep._create_replay_map(self.tmpdir.name, ["PASS"])
        exp = [test.ReplaySkipTest, test.ReplaySkipTest, None,
               test.ReplaySkipTest, test.ReplaySkipTest]
        self.assertEqual(act, exp)
        act = rep._create_replay_map(self.tmpdir.name, ["INTERRUPTED"])
        exp = [None, test.ReplaySkipTest, test.ReplaySkipTest, None, None]
        self.assertEqual(act, exp)

    def test_tap_parsing(self):
        """
        Check various ugly tap results
        """
        rep = replay_legacy.Replay()
        res_path = os.path.join(self.tmpdir.name, "results.tap")
        self.assertEqual(rep._get_tests_from_tap(res_path), None)
        with open(res_path, "w") as res:
            res.write("\n# 1..5\n")
        self.assertEqual(rep._get_tests_from_tap(res_path), None)
        with open(res_path, "w") as res:
            res.write("\n1..5\n")
        exp = [{"test": "UNKNOWN", "status": "INTERRUPTED"}] * 5
        self.assertEqual(rep._get_tests_from_tap(res_path), exp)
        with open(res_path, "w") as res:
            res.write("ok 5 fdfafdsfa  # SKIP for no reason")
        exp = ([{"test": "UNKNOWN", "status": "INTERRUPTED"}] * 4 +
               [{"test": "fdfafdsfa", "status": "SKIP"}])
        self.assertEqual(rep._get_tests_from_tap(res_path), exp)


if __name__ == '__main__':
    unittest.main()
