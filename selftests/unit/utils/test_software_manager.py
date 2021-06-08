import os
import shutil
import unittest

from avocado.utils import distro, software_manager
from selftests.utils import setup_avocado_loggers

setup_avocado_loggers()


def apt_supported_distro():
    """Distros we expect to have the apt backend selected."""
    return distro.detect().name in ['debian', 'Ubuntu']


class SoftwareManager(unittest.TestCase):
    def setUp(self):
        self.destination = '/tmp/avocado_rpms'
        self.rpm_path = os.path.abspath(
            os.path.join(os.path.dirname(os.path.dirname(__file__)),
                         os.path.pardir, ".data", "hello.rpm"))
        self.deb_path = os.path.abspath(
            os.path.join(os.path.dirname(os.path.dirname(__file__)),
                         os.path.pardir, ".data", "hello.deb"))

    def test_extract_from_rpm(self):
        manager = software_manager.SoftwareManager()
        result = manager.extract_from_package(self.rpm_path,
                                              self.destination)
        self.assertEqual(self.destination, result)

    def test_extract_from_deb(self):
        manager = software_manager.SoftwareManager()
        result = manager.extract_from_package(self.deb_path,
                                              self.destination)
        self.assertEqual(self.destination, result)

    def test_extract_permission(self):
        manager = software_manager.SoftwareManager()
        with self.assertRaises(NotImplementedError) as context:
            manager.extract_from_package('/dev/null', self.destination)
        expected = 'No package manager supported was found for package '
        self.assertTrue(expected in str(context.exception))

    def tearDown(self):
        shutil.rmtree('/tmp/avocado_rpms', True)


@unittest.skipUnless(os.getuid() == 0, "This test requires root privileges")
@unittest.skipUnless(apt_supported_distro(), "Unsupported distro")
class Apt(unittest.TestCase):

    def test_provides(self):
        sm = software_manager.SoftwareManager()
        self.assertEqual(sm.provides('/bin/login'), 'login')
        self.assertTrue(isinstance(sm.backend,
                                   software_manager.backends.apt.AptBackend))


if __name__ == '__main__':
    unittest.main()
