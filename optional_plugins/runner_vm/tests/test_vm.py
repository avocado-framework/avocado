import tempfile
import unittest.mock

from avocado.core.job import Job

import avocado_runner_vm

from selftests import temp_dir_prefix


class _FakeVM(avocado_runner_vm.VM):

    """
    Fake VM-inherited object (it's better to inherit it, than to mock the
    isinstance)
    """

    def __init__(self):  # pylint: disable=W0231
        # don't call avocado_runner_vm.VM.__init__
        self.start = None
        self.create_snapshot = None
        self.stop = None
        self.restore_snapshot = None
        self.snapshot = True
        self.domain = unittest.mock.Mock()
        self.domain.isActive = unittest.mock.Mock(return_value=True)


class VMTestRunnerSetup(unittest.TestCase):

    """ Tests the VMTestRunner setup() method """

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    def test_setup(self):
        mock_vm = _FakeVM()
        mock_vm.start = unittest.mock.Mock(return_value=True)
        mock_vm.create_snapshot = unittest.mock.Mock()
        mock_vm.stop = unittest.mock.Mock()
        mock_vm.restore_snapshot = unittest.mock.Mock()
        job_args = {'test_result_total': 1,
                    'vm_domain': 'domain',
                    'vm_username': 'username',
                    'vm_hostname': 'hostname',
                    'vm_port': 22,
                    'vm_password': 'password',
                    'vm_key_file': None,
                    'vm_cleanup': True,
                    'vm_no_copy': False,
                    'vm_timeout': 120,
                    'vm_hypervisor_uri': 'my_hypervisor_uri',
                    'reference': ['/tests/sleeptest.py',
                                  '/tests/other/test',
                                  'passtest.py'],
                    'env_keep': None,
                    'base_logdir': self.tmpdir.name,
                    'run.keep_tmp': 'on',
                    'run.store_logging_stream': [],
                    'run.dry_run.enabled': True}
        with Job(job_args) as job:
            with unittest.mock.patch('avocado_runner_vm.vm_connect',
                                     return_value=mock_vm):
                # VMTestRunner()
                runner = avocado_runner_vm.VMTestRunner()
                runner.setup(job)
                runner.tear_down(job)
                mock_vm.start.assert_called_once_with()
                mock_vm.create_snapshot.assert_called_once_with()
                mock_vm.stop.assert_called_once_with()
                mock_vm.restore_snapshot.assert_called_once_with()

    def tearDown(self):
        try:
            self.tmpdir.cleanup()
            # may have been clean up already on job.cleanup()
        except FileNotFoundError:
            pass


if __name__ == '__main__':
    unittest.main()
