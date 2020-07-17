import unittest

from avocado.core.result import Result

UNIQUE_ID = '0000000000000000000000000000000000000000'
LOGFILE = None


class ResultTest(unittest.TestCase):

    def test_result_no_job_id(self):
        with self.assertRaises(TypeError):
            Result()

    def test_result_no_job_logfile(self):
        with self.assertRaises(TypeError):
            Result(UNIQUE_ID)

    def test_result_rate_all_succeeded(self):
        result = Result(UNIQUE_ID, LOGFILE)
        result.check_test({'status': 'PASS'})
        result.end_tests()
        self.assertEqual(result.rate, 100.0)

    def test_result_rate_all_succeeded_with_warns(self):
        result = Result(UNIQUE_ID, LOGFILE)
        result.check_test({'status': 'PASS'})
        result.check_test({'status': 'WARN'})
        result.end_tests()
        self.assertEqual(result.rate, 100.0)

    def test_result_rate_all_succeeded_with_skips(self):
        result = Result(UNIQUE_ID, LOGFILE)
        result.check_test({'status': 'PASS'})
        result.check_test({'status': 'SKIP'})
        result.end_tests()
        self.assertEqual(result.rate, 100.0)

    def test_result_rate_all_succeeded_with_cancelled(self):
        result = Result(UNIQUE_ID, LOGFILE)
        result.check_test({'status': 'PASS'})
        result.check_test({'status': 'CANCEL'})
        result.end_tests()
        self.assertEqual(result.rate, 100.0)

    def test_result_rate_half_succeeded(self):
        result = Result(UNIQUE_ID, LOGFILE)
        result.check_test({'status': 'PASS'})
        result.check_test({'status': 'FAIL'})
        result.end_tests()
        self.assertEqual(result.rate, 50.0)

    def test_result_rate_none_succeeded(self):
        result = Result(UNIQUE_ID, LOGFILE)
        result.check_test({'status': 'FAIL'})
        result.end_tests()
        self.assertEqual(result.rate, 0.0)


if __name__ == '__main__':
    unittest.main()
