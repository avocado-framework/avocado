import argparse
import unittest

from avocado.core.result import Result


class FakeJobMissingUniqueId(object):

    def __init__(self, args):
        self.args = args


class FakeJob(object):

    def __init__(self, args):
        self.args = args
        self.unique_id = '0000000000000000000000000000000000000000'


class ResultTest(unittest.TestCase):

    def test_result_job_without_id(self):
        args = argparse.Namespace()
        Result(FakeJob(args))
        self.assertRaises(AttributeError, Result, FakeJobMissingUniqueId(args))

    def test_result_rate_all_succeeded(self):
        result = Result(FakeJob([]))
        result.check_test({'status': 'PASS'})
        result.end_tests()
        self.assertEquals(result.rate, 100.0)

    def test_result_rate_all_succeeded_with_warns(self):
        result = Result(FakeJob([]))
        result.check_test({'status': 'PASS'})
        result.check_test({'status': 'WARN'})
        result.end_tests()
        self.assertEquals(result.rate, 100.0)

    def test_result_rate_all_succeeded_with_skips(self):
        result = Result(FakeJob([]))
        result.check_test({'status': 'PASS'})
        result.check_test({'status': 'SKIP'})
        result.end_tests()
        self.assertEquals(result.rate, 100.0)

    def test_result_rate_all_succeeded_with_cancelled(self):
        result = Result(FakeJob([]))
        result.check_test({'status': 'PASS'})
        result.check_test({'status': 'CANCEL'})
        result.end_tests()
        self.assertEquals(result.rate, 100.0)

    def test_result_rate_half_succeeded(self):
        result = Result(FakeJob([]))
        result.check_test({'status': 'PASS'})
        result.check_test({'status': 'FAIL'})
        result.end_tests()
        self.assertEquals(result.rate, 50.0)

    def test_result_rate_none_succeeded(self):
        result = Result(FakeJob([]))
        result.check_test({'status': 'FAIL'})
        result.end_tests()
        self.assertEquals(result.rate, 0.0)


if __name__ == '__main__':
    unittest.main()
