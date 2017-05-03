import unittest

from flexmock import flexmock, flexmock_teardown

import avocado_runner_vm


JSON_RESULTS = ('Something other than json\n'
                '{"tests": [{"test": "sleeptest.1", "url": "sleeptest", '
                '"status": "PASS", "time": 1.23, "start": 0, "end": 1.23}],'
                '"debuglog": "/home/user/avocado/logs/run-2014-05-26-15.45.'
                '37/debug.log", "errors": 0, "skip": 0, "time": 1.4, '
                '"start": 0, "end": 1.4, "pass": 1, "failures": 0, "total": '
                '1}\nAdditional stuff other than json')


class _FakeVM(avocado_runner_vm.VM):

    """
    Fake VM-inherited object (it's better to inherit it, than to flexmock the
    isinstance)
    """
    def __init__(self):  # pylint: disable=W0231
        # don't call avocado_runner_vm.VM.__init__
        self.snapshot = True
        self.domain = flexmock(isActive=lambda: True)


class VMTestRunnerSetup(unittest.TestCase):

    """ Tests the VMTestRunner setup() method """

    def setUp(self):
        mock_vm = flexmock(_FakeVM())
        flexmock(avocado_runner_vm).should_receive('vm_connect').and_return(mock_vm).once().ordered()
        mock_vm.should_receive('start').and_return(True).once().ordered()
        mock_vm.should_receive('create_snapshot').once().ordered()
        # VMTestRunner()
        Args = flexmock(test_result_total=1,
                        url=['/tests/sleeptest', '/tests/other/test',
                             'passtest'],
                        vm_domain='domain',
                        vm_username='username',
                        vm_hostname='hostname',
                        vm_port=22,
                        vm_password='password',
                        vm_key_file=None,
                        vm_cleanup=True,
                        vm_no_copy=False,
                        vm_timeout=120,
                        vm_hypervisor_uri='my_hypervisor_uri',
                        env_keep=None)
        log = flexmock()
        log.should_receive("info")
        job = flexmock(args=Args, log=log)
        self.runner = avocado_runner_vm.VMTestRunner(job, None)
        mock_vm.should_receive('stop').once().ordered()
        mock_vm.should_receive('restore_snapshot').once().ordered()

    def tearDown(self):
        flexmock_teardown()

    def test_setup(self):
        """ Tests VMTestRunner.setup() """
        self.runner.setup()
        self.runner.tear_down()
        flexmock_teardown()


if __name__ == '__main__':
    unittest.main()
