import os
import re
import sys
import unittest

from flexmock import flexmock


# simple magic for using scripts within a source tree
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
basedir = os.path.dirname(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)


from avocado.linux import distro


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

        flexmock(os.path)
        os.path.should_receive('exists').and_return(True)
        my_probe = MyProbe()
        probed_distro_name = my_probe.name_for_file()
        self.assertEqual(distro_name, probed_distro_name)


if __name__ == '__main__':
    unittest.main()
