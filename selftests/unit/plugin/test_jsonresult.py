import json
import os
import unittest

from avocado import Test
from avocado.core import job
from avocado.core.result import Result
from avocado.plugins import jsonresult
from selftests.utils import TestCaseTmpDir, setup_avocado_loggers

setup_avocado_loggers()


UNIQUE_ID = '0000000000000000000000000000000000000000'
LOGFILE = None


class JSONResultTest(TestCaseTmpDir):

    def setUp(self):
        super().setUp()

        class SimpleTest(Test):

            def test(self):
                pass

        json_output_path = os.path.join(self.tmpdir.name, 'results.json')
        config = {'run.results_dir': self.tmpdir.name,
                  'job.run.result.json.output': json_output_path}
        self.job = job.Job(config)
        self.job.setup()
        self.test_result = Result(UNIQUE_ID, LOGFILE)
        self.test_result.filename = json_output_path
        self.test_result.tests_total = 1
        self.test1 = SimpleTest(config=self.job.config, base_logdir=self.tmpdir.name)
        self.test1._Test__status = 'PASS'
        self.test1.time_elapsed = 1.23

    def test_add_success(self):
        self.test_result.start_test(self.test1)
        self.test_result.end_test(self.test1.get_state())
        self.test_result.end_tests()
        json_result = jsonresult.JSONResult()
        json_result.render(self.test_result, self.job)
        with open(self.job.config.get('job.run.result.json.output'), encoding='utf-8') as fp:
            j = fp.read()
        obj = json.loads(j)
        self.assertTrue(obj)
        self.assertEqual(len(obj['tests']), 1)

    def test_add_several_statuses(self):
        def run_fake_status(status):
            self.test_result.start_test(self.test1)
            self.test_result.check_test(status)

        def check_item(name, value, exp):
            self.assertEqual(value, exp,
                             f"Result{name} is {value} and not {exp}\n{res}")

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
        json_result = jsonresult.JSONResult()
        json_result.render(self.test_result, self.job)
        output = self.job.config.get('job.run.result.json.output')
        with open(output, encoding='utf-8') as json_output:
            res = json.loads(json_output.read())
        check_item("[pass]", res["pass"], 2)
        check_item("[errors]", res["errors"], 4)
        check_item("[failures]", res["failures"], 1)
        check_item("[skip]", res["skip"], 4)
        check_item("[total]", res["total"], 13)

    def test_negative_status(self):
        def check_item(name, value, exp):
            self.assertEqual(value, exp,
                             f"Result{name} is {value} and not {exp}\n{res}")

        self.test_result.tests_total = 0
        self.test_result.start_test(self.test1)
        self.test_result.check_test(self.test1.get_state())
        self.test_result.end_tests()
        json_result = jsonresult.JSONResult()
        json_result.render(self.test_result, self.job)
        output = self.job.config.get('job.run.result.json.output')
        with open(output, encoding='utf-8') as json_output:
            res = json.loads(json_output.read())
        check_item("[total]", res["total"], 1)
        check_item("[skip]", res["skip"], 0)
        check_item("[pass]", res["pass"], 1)

    def tearDown(self):
        self.job.cleanup()
        super().tearDown()


if __name__ == '__main__':
    unittest.main()
