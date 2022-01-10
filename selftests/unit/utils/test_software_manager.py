import os
import unittest

from avocado.utils import distro
from avocado.utils.software_manager import backends, manager
from selftests.utils import BASEDIR, setup_avocado_loggers

setup_avocado_loggers()


def apt_supported_distro():
    """Distros we expect to have the apt backend selected."""
    return distro.detect().name in ['debian', 'Ubuntu']


@unittest.skipUnless(os.getuid() == 0, "This test requires root privileges")
@unittest.skipUnless(apt_supported_distro(), "Unsupported distro")
class Apt(unittest.TestCase):

    def test_provides(self):
        sm = manager.SoftwareManager()
        self.assertEqual(sm.provides('/bin/login'), 'login')
        self.assertTrue(isinstance(sm.backend,
                                   backends.apt.AptBackend))


class Dpkg(unittest.TestCase):

    def test_is_valid(self):
        deb_path = os.path.join(BASEDIR, 'selftests', '.data', 'hello.deb')
        dpkg = backends.dpkg.DpkgBackend
        self.assertTrue(dpkg.is_valid(deb_path))

    def test_is_not_valid(self):
        not_deb_path = os.path.join(BASEDIR, 'selftests', '.data', 'guaca.a')
        dpkg = backends.dpkg.DpkgBackend
        self.assertFalse(dpkg.is_valid(not_deb_path))


if __name__ == '__main__':
    unittest.main()
