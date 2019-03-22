import re
import unittest.mock

from avocado.utils import distro


class ProbeTest(unittest.TestCase):

    def test_check_name_for_file_fail(self):
        class MyProbe(distro.Probe):
            CHECK_FILE = '/etc/issue'

        my_probe = MyProbe()
        self.assertFalse(my_probe.check_name_for_file())

    def test_check_name_for_file(self):
        class MyProbe(distro.Probe):
            CHECK_FILE = '/etc/issue'
            CHECK_FILE_DISTRO_NAME = 'superdistro'

        my_probe = MyProbe()
        self.assertTrue(my_probe.check_name_for_file())

    def test_check_name_for_file_contains_fail(self):
        class MyProbe(distro.Probe):
            CHECK_FILE = '/etc/issue'
            CHECK_FILE_CONTAINS = 'text'

        my_probe = MyProbe()
        self.assertFalse(my_probe.check_name_for_file_contains())

    def test_check_name_for_file_contains(self):
        class MyProbe(distro.Probe):
            CHECK_FILE = '/etc/issue'
            CHECK_FILE_CONTAINS = 'text'
            CHECK_FILE_DISTRO_NAME = 'superdistro'

        my_probe = MyProbe()
        self.assertTrue(my_probe.check_name_for_file_contains())

    def test_check_version_fail(self):
        class MyProbe(distro.Probe):
            CHECK_VERSION_REGEX = re.compile(r'distro version (\d+)')

        my_probe = MyProbe()
        self.assertFalse(my_probe.check_version())

    def test_version_returnable(self):
        class MyProbe(distro.Probe):
            CHECK_FILE = '/etc/distro-release'
            CHECK_VERSION_REGEX = re.compile(r'distro version (\d+)')

        my_probe = MyProbe()
        self.assertTrue(my_probe.check_version())

    def test_name_for_file(self):
        distro_file = '/etc/superdistro-issue'
        distro_name = 'superdistro'

        class MyProbe(distro.Probe):
            CHECK_FILE = distro_file
            CHECK_FILE_DISTRO_NAME = distro_name

        my_probe = MyProbe()
        with unittest.mock.patch('avocado.utils.distro.os.path.exists',
                                 return_value=True) as mocked:
            probed_distro_name = my_probe.name_for_file()
            mocked.assert_called_once_with(distro_file)
        self.assertEqual(distro_name, probed_distro_name)


class DetectTest(unittest.TestCase):

    def test_rhel_7_6(self):
        open_mocked = unittest.mock.mock_open(
            read_data='Red Hat Enterprise Linux Server release 7.6 (Maipo)\n')
        with unittest.mock.patch('builtins.open', open_mocked):
            detected = distro.RedHatProbe().get_distro()
        self.assertEqual(detected.name, 'rhel')
        self.assertEqual(detected.version, '7')
        self.assertEqual(detected.release, '6')

    def test_rhel_8_0(self):
        open_mocked = unittest.mock.mock_open(
            read_data='Red Hat Enterprise Linux release 8.0 (Ootpa)\n')
        with unittest.mock.patch('builtins.open', open_mocked):
            detected = distro.RedHatProbe().get_distro()
        self.assertEqual(detected.name, 'rhel')
        self.assertEqual(detected.version, '8')
        self.assertEqual(detected.release, '0')


if __name__ == '__main__':
    unittest.main()
