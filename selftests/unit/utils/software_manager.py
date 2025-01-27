import os
import unittest

from avocado.utils import distro
from avocado.utils.software_manager import backends, manager
from selftests.utils import BASEDIR, setup_avocado_loggers

setup_avocado_loggers()


def apt_supported_distro():
    """Distros we expect to have the apt backend selected."""
    return distro.detect().name in ["debian", "Ubuntu"]


def login_binary_path(distro_name, distro_version):
    """Retrieve the login binary path based on the distro version"""
    if distro_name == "Ubuntu":
        if float(distro_version) >= 24.04:
            return "/usr/bin/login"
    if distro_name == "debian":
        if distro_version == "sid" or int(distro_version) >= 14:
            return "/usr/bin/login"
    return "/bin/login"


@unittest.skipUnless(os.getuid() == 0, "This test requires root privileges")
@unittest.skipUnless(apt_supported_distro(), "Unsupported distro")
class Apt(unittest.TestCase):
    def test_provides(self):
        sm = manager.SoftwareManager()
        _distro = distro.detect()
        login_path = login_binary_path(_distro.name, _distro.version)
        self.assertEqual(sm.provides(login_path), "login")
        self.assertTrue(isinstance(sm.backend, backends.apt.AptBackend))


class Dpkg(unittest.TestCase):
    def test_is_valid(self):
        deb_path = os.path.join(BASEDIR, "selftests", ".data", "hello.deb")
        dpkg = backends.dpkg.DpkgBackend
        self.assertTrue(dpkg.is_valid(deb_path))

    def test_is_not_valid(self):
        not_deb_path = os.path.join(BASEDIR, "selftests", ".data", "guaca.a")
        dpkg = backends.dpkg.DpkgBackend
        self.assertFalse(dpkg.is_valid(not_deb_path))


if __name__ == "__main__":
    unittest.main()
