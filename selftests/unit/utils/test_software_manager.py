import os
import unittest

from avocado.utils import distro, software_manager
from selftests.utils import setup_avocado_loggers

setup_avocado_loggers()


def apt_supported_distro():
    """Distros we expect to have the apt backend selected."""
    return distro.detect().name in ['debian', 'Ubuntu']


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
