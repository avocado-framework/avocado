import argparse
import shutil
import unittest
try:
    from unittest import mock
except ImportError:
    import mock

from avocado.core.job import Job
import avocado_runner_vm


class _FakeVM(avocado_runner_vm.VM):

    """
    Fake VM-inherited object (it's better to inherit it, than to mock the
    isinstance)
    """

    def __init__(self):  # pylint: disable=W0231
        # don't call avocado_runner_vm.VM.__init__
        self.snapshot = True
        self.domain = mock.Mock()
        self.domain.isActive = mock.Mock(return_value=True)


class VMTestRunnerSetup(unittest.TestCase):

    """ Tests the VMTestRunner setup() method """

    def test_setup(self):
        mock_vm = _FakeVM()
        mock_vm.start = mock.Mock(return_value=True)
        mock_vm.create_snapshot = mock.Mock()
        mock_vm.stop = mock.Mock()
        mock_vm.restore_snapshot = mock.Mock()
        job_args = argparse.Namespace(test_result_total=1,
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
                                      reference=['/tests/sleeptest.py',
                                                 '/tests/other/test',
                                                 'passtest.py'],
                                      dry_run=True,
                                      env_keep=None)
        try:
            job = Job(job_args)
            with mock.patch('avocado_runner_vm.vm_connect',
                            return_value=mock_vm):
                # VMTestRunner()
                runner = avocado_runner_vm.VMTestRunner(job, None)
                runner.setup()
                runner.tear_down()
                mock_vm.start.assert_called_once_with()
                mock_vm.create_snapshot.assert_called_once_with()
                mock_vm.stop.assert_called_once_with()
                mock_vm.restore_snapshot.assert_called_once_with()
        finally:
            shutil.rmtree(job.args.base_logdir)


if __name__ == '__main__':
    unittest.main()
