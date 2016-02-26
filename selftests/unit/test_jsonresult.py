import unittest
import os
import json
import argparse
import tempfile
import shutil

from avocado import Test
from avocado.core import jsonresult
from avocado.core import job


class FakeJob(object):
    def __init__(self, args):
        self.args = args


class JSONResultTest(unittest.TestCase):

    def setUp(self):

        class SimpleTest(Test):

            def test(self):
                pass

        self.tmpfile = tempfile.mkstemp()
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        args = argparse.Namespace(json_output=self.tmpfile[1])
        self.test_result = jsonresult.JSONTestResult(FakeJob(args))
        self.test_result.filename = self.tmpfile[1]
        self.test_result.start_tests()
        self.test1 = SimpleTest(job=job.Job(), base_logdir=self.tmpdir)
        self.test1.status = 'PASS'
        self.test1.time_elapsed = 1.23

    def tearDown(self):
        os.close(self.tmpfile[0])
        os.remove(self.tmpfile[1])
        shutil.rmtree(self.tmpdir)

    def testAddSuccess(self):
        self.test_result.start_test(self.test1)
        self.test_result.end_test(self.test1.get_state())
        self.test_result.end_tests()
        self.assertTrue(self.test_result.json)
        with open(self.test_result.filename) as fp:
            j = fp.read()
        obj = json.loads(j)
        self.assertTrue(obj)
        self.assertEqual(len(obj['tests']), 1)


if __name__ == '__main__':
    unittest.main()
