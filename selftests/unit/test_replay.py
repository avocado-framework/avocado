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
        exp = [None, test.ReplaySkipTest, test.ReplaySkipTest, test.ReplaySkipTest, test.ReplaySkipTest]
        self.assertEqual(act, exp)
        act = rep._create_replay_map(self.tmpdir, ["INTERRUPTED"])
        exp = [test.ReplaySkipTest, None, None, None, None]
        self.assertEqual(act, exp)


if __name__ == '__main__':
    unittest.main()
