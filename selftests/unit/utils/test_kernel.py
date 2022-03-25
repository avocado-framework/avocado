import unittest

from avocado.utils.kernel import KernelBuild
from selftests.utils import setup_avocado_loggers

setup_avocado_loggers()


class TestKernelBuild(unittest.TestCase):
    def setUp(self):
        self.kernel_version = '4.4.133'
        self.kernel = KernelBuild(self.kernel_version)

    def test_build_default_url(self):
        expected_url = 'https://www.kernel.org/pub/linux/kernel/v4.x/linux-4.4.133.tar.gz'
        self.assertEqual(self.kernel._build_kernel_url(), expected_url)

    def test_build_overrided_url(self):
        base_url = 'https://mykernel.com/'
        expected_url = f'{base_url}linux-4.4.133.tar.gz'
        self.assertEqual(self.kernel._build_kernel_url(base_url=base_url), expected_url)

    def tearDown(self):
        # To make sure that the temporary workdir is cleaned up
        del(self.kernel)
