import json
from os import path

from avocado.utils import process
from selftests.utils import AVOCADO, TestCaseTmpDir


class JsonResultTest(TestCaseTmpDir):

    def test_logfile(self):
        cmd_line = ('%s run examples/tests/failtest.py '
                    '--job-results-dir %s --disable-sysinfo ' %
                    (AVOCADO, self.tmpdir.name))
        process.run(cmd_line, ignore_status=True)
        json_path = path.join(self.tmpdir.name, 'latest', 'results.json')

        with open(json_path, 'r') as json_file:
            data = json.load(json_file)
            test_data = data['tests'].pop()
            expected_logfile = path.join(test_data['logdir'], 'debug.log')
            self.assertEqual(expected_logfile, test_data['logfile'])

    def test_fail_reason(self):
        cmd_line = ('%s run examples/tests/failtest.py '
                    '--job-results-dir %s --disable-sysinfo ' %
                    (AVOCADO, self.tmpdir.name))
        process.run(cmd_line, ignore_status=True)
        json_path = path.join(self.tmpdir.name, 'latest', 'results.json')
        with open(json_path, 'r') as json_file:
            data = json.load(json_file)
            test_data = data['tests'].pop()
            self.assertEqual('This test is supposed to fail',
                             test_data['fail_reason'])
