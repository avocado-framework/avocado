import os
import shutil
import tempfile
import unittest

from avocado.core import test
from avocado.plugins import replay


class Replay(unittest.TestCase):

    """
    avocado.plugins.Replay unittests
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_replay_map_interrupted_json(self):
        """
        Make sure unexecuted tests are appended
        """
        with open(os.path.join(self.tmpdir, "results.json"), "w") as res:
            res.write('{"skip": 3, "tests": [{"test": "executed", "status":'
                      '"PASS"}], "total": 4}')
        rep = replay.Replay()
        act = rep._create_replay_map(self.tmpdir, ["PASS"])
        exp = [None, test.ReplaySkipTest, test.ReplaySkipTest,
               test.ReplaySkipTest, test.ReplaySkipTest]
        self.assertEqual(act, exp)
        act = rep._create_replay_map(self.tmpdir, ["INTERRUPTED"])
        exp = [test.ReplaySkipTest, None, None, None, None]
        self.assertEqual(act, exp)

    def test_replay_map_after_crash(self):
        """
        Tests the fallback to TAP as the source of executed tests when
        JSON was not generated
        """
        with open(os.path.join(self.tmpdir, "results.tap"), "w") as res:
            res.write("\n# 1..10\nok 3 test3\nnot ok 2 test2\n1..5")
        rep = replay.Replay()
        act = rep._create_replay_map(self.tmpdir, ["PASS"])
        exp = [test.ReplaySkipTest, test.ReplaySkipTest, None,
               test.ReplaySkipTest, test.ReplaySkipTest]
        self.assertEqual(act, exp)
        act = rep._create_replay_map(self.tmpdir, ["INTERRUPTED"])
        exp = [None, test.ReplaySkipTest, test.ReplaySkipTest, None, None]
        self.assertEqual(act, exp)

    def test_tap_parsing(self):
        """
        Check various ugly tap results
        """
        rep = replay.Replay()
        res_path = os.path.join(self.tmpdir, "results.tap")
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
