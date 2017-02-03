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
        result = Result(FakeJob(args))
        self.assertRaises(AttributeError, Result, FakeJobMissingUniqueId(args))


if __name__ == '__main__':
    unittest.main()
