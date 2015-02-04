#!/usr/bin/env python

import unittest

from flexmock import flexmock, flexmock_teardown

from avocado.plugins import vm, remote


JSON_RESULTS = ('Something other than json\n'
                '{"tests": [{"test": "sleeptest.1", "url": "sleeptest", '
                '"status": "PASS", "time": 1.23, "start": 0, "end": 1.23}],'
                '"debuglog": "/home/user/avocado/logs/run-2014-05-26-15.45.'
                '37/debug.log", "errors": 0, "skip": 0, "time": 1.4, '
                '"start": 0, "end": 1.4, "pass": 1, "failures": 0, "total": '
                '1}\nAdditional stuff other than json')


class VMTestResultTest(unittest.TestCase):

    """ Tests the VMTestResult """

    def setUp(self):
        # remote.RemoteTestResult.__init__()
        Stream = flexmock()
        (flexmock(remote.os).should_receive('getcwd')
         .and_return('/current/directory').once().ordered())
        # vm.VMTestResult.setup()
        (Stream.should_receive('notify')
         .with_args(msg="DOMAIN     : domain", event="message"))
        mock_vm = flexmock(snapshot=True,
                           domain=flexmock(isActive=lambda: True))
        virt = flexmock(vm.virt)
        virt.should_receive('vm_connect').and_return(mock_vm).once().ordered()
        mock_vm.should_receive('start').and_return(True).once().ordered()
        mock_vm.should_receive('create_snapshot').once().ordered()
        RemoteTestResult = flexmock(remote.RemoteTestResult)
        RemoteTestResult.should_receive('setup').once().ordered()
        # vm.RemoteTestResult()
        Args = flexmock(test_result_total=1,
                        url=['/tests/sleeptest', '/tests/other/test',
                             'passtest'],
                        vm_domain='domain',
                        vm_username='username',
                        vm_hostname='hostname',
                        vm_port=22,
                        vm_password='password',
                        vm_cleanup=True,
                        vm_no_copy=False,
                        vm_hypervisor_uri='my_hypervisor_uri')
        self.remote = vm.VMTestResult(Stream, Args)
        # vm.RemoteTestResult.tear_down()
        RemoteTestResult.should_receive('tear_down').once().ordered()
        mock_vm.should_receive('restore_snapshot').once().ordered()

    def tearDown(self):
        flexmock_teardown()

    def test_setup(self):
        """ Tests VMTestResult.test_setup() """
        self.remote.setup()
        self.remote.tear_down()
        flexmock_teardown()

if __name__ == '__main__':
    unittest.main()
