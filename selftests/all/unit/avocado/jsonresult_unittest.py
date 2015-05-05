import unittest
import os
import sys
import json
import argparse
import tempfile
import shutil

# simple magic for using scripts within a source tree
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
basedir = os.path.dirname(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.core.plugins import jsonresult
from avocado import test
from avocado.core import job


class _Stream(object):

    def start_file_logging(self, param1, param2):
        pass

    def stop_file_logging(self):
        pass

    def set_tests_info(self, info):
        pass

    def notify(self, event, msg):
        pass

    def add_test(self, state):
        pass

    def set_test_status(self, status, state):
        pass


class JSONResultTest(unittest.TestCase):

    def setUp(self):
        self.tmpfile = tempfile.mkstemp()
        self.tmpdir = tempfile.mkdtemp()
        args = argparse.Namespace(json_output=self.tmpfile[1])
        stream = _Stream()
        stream.logfile = 'debug.log'
        self.test_result = jsonresult.JSONTestResult(stream, args)
        self.test_result.filename = self.tmpfile[1]
        self.test_result.start_tests()
        self.test1 = test.Test(job=job.Job(), base_logdir=self.tmpdir)
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
