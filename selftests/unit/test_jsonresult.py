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

    def testAddSeveralStatuses(self):
        def run_fake_status(status):
            self.test_result.start_test(self.test1)
            self.test_result.check_test(status)

        def check_item(name, value, exp):
            self.assertEqual(value, exp, "Result%s is %s and not %s\n%s"
                             % (name, value, exp, res))

        # Set the number of tests to all tests + 3
        self.test_result.tests_total = 13
        # Full PASS status
        self.test_result.start_test(self.test1)
        self.test_result.check_test(self.test1.get_state())
        # Only status - valid statuses
        run_fake_status({"status": "PASS"})
        run_fake_status({"status": "SKIP"})
        run_fake_status({"status": "FAIL"})
        run_fake_status({"status": "ERROR"})
        run_fake_status({"status": "WARN"})
        run_fake_status({"status": "INTERRUPTED"})
        # Only status - invalid statuses
        run_fake_status({"status": "INVALID"})
        run_fake_status({"status": None})
        run_fake_status({"status": ""})
        # Postprocess
        self.test_result.end_tests()
        res = json.loads(self.test_result.json)
        check_item("[pass]", res["pass"], 2)
        check_item("[errors]", res["errors"], 4)
        check_item("[failures]", res["failures"], 1)
        check_item("[skip]", res["skip"], 4)
        check_item("[total]", res["total"], 13)

    def testNegativeStatus(self):
        def check_item(name, value, exp):
            self.assertEqual(value, exp, "Result%s is %s and not %s\n%s"
                             % (name, value, exp, res))

        self.test_result.tests_total = 0
        self.test_result.start_test(self.test1)
        self.test_result.check_test(self.test1.get_state())
        self.test_result.end_tests()
        res = json.loads(self.test_result.json)
        check_item("[total]", res["total"], 1)
        check_item("[skip]", res["skip"], 0)
        check_item("[pass]", res["pass"], 1)


if __name__ == '__main__':
    unittest.main()
