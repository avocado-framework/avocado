import json
from os import path

from avocado.utils import process, script
from avocado.utils.network import find_free_port
from selftests.utils import AVOCADO, TestCaseTmpDir


class JsonResultTest(TestCaseTmpDir):

    def setUp(self):
        super(JsonResultTest, self).setUp()
        status_server = '127.0.0.1:%u' % find_free_port()
        self.config_file = script.TemporaryScript(
            'avocado.conf',
            ("[nrunner]\n"
             "status_server_listen = %s\n"
             "status_server_uri = %s\n") % (status_server, status_server))
        self.config_file.save()

    def test_logfile(self):
        cmd_line = ('%s --config %s run --test-runner=nrunner '
                    'examples/tests/failtest.py '
                    '--job-results-dir %s --disable-sysinfo ' %
                    (AVOCADO, self.config_file.path, self.tmpdir.name))
        process.run(cmd_line, ignore_status=True)
        json_path = path.join(self.tmpdir.name, 'latest', 'results.json')

        with open(json_path, 'r') as json_file:
            data = json.load(json_file)
            test_data = data['tests'].pop()
            expected_logfile = path.join(test_data['logdir'], 'debug.log')
            self.assertEqual(expected_logfile, test_data['logfile'])

    def test_fail_reason(self):
        cmd_line = ('%s --config %s run --test-runner=nrunner '
                    'examples/tests/failtest.py '
                    '--job-results-dir %s --disable-sysinfo ' %
                    (AVOCADO, self.config_file.path, self.tmpdir.name))
        process.run(cmd_line, ignore_status=True)
        json_path = path.join(self.tmpdir.name, 'latest', 'results.json')
        with open(json_path, 'r') as json_file:
            data = json.load(json_file)
            test_data = data['tests'].pop()
            self.assertEqual('This test is supposed to fail',
                             test_data['fail_reason'])

    def tearDown(self):
        super(JsonResultTest, self).tearDown()
        self.config_file.remove()
