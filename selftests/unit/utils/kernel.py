import unittest

from avocado.utils.kernel import KernelBuild, _parse_kernel_version
from selftests.utils import setup_avocado_loggers

setup_avocado_loggers()


class TestKernelBuild(unittest.TestCase):
    def setUp(self):
        self.kernel_version = "4.4.133"
        self.kernel = KernelBuild(self.kernel_version)

    def test_build_default_url(self):
        expected_url = (
            "https://www.kernel.org/pub/linux/kernel/v4.x/linux-4.4.133.tar.gz"
        )
        self.assertEqual(self.kernel._build_kernel_url(), expected_url)

    def test_build_overrided_url(self):
        base_url = "https://mykernel.com/"
        expected_url = f"{base_url}linux-4.4.133.tar.gz"
        self.assertEqual(self.kernel._build_kernel_url(base_url=base_url), expected_url)

    def tearDown(self):
        # To make sure that the temporary workdir is cleaned up
        del self.kernel


class Version(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_parse_kernel_version("1.2.3-100"), (1, 2, 3, 100))

    def test_uname(self):
        self.assertEqual(_parse_kernel_version("9.0.1-100.fc50.x86_64"), (9, 0, 1, 100))

    def test_malformed_incomplete(self):
        with self.assertRaises(AssertionError):
            _parse_kernel_version("1.2")
