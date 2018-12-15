import os
import unittest

from avocado.utils import distro
from avocado.utils import software_manager

from .. import setup_avocado_loggers


setup_avocado_loggers()


def apt_supported_distro():
    """
    The only Linux distributions this was tested on
    """
    this = distro.detect()
    if this.name == 'debian':
        return this.version == '9' and this.release == '6'
    elif this.name == 'Ubuntu':
        return this.version == '18' and this.release == '04'
    return False


@unittest.skipUnless(os.getuid() == 0, "This test requires root privileges")
@unittest.skipUnless(apt_supported_distro(), "Unsupported distro")
class Apt(unittest.TestCase):

    def test_provides(self):
        sm = software_manager.SoftwareManager()
        self.assertEqual(sm.provides('/bin/login'), 'login')
        self.assertTrue(isinstance(sm.backend, software_manager.AptBackend))


if __name__ == '__main__':
    unittest.main()
