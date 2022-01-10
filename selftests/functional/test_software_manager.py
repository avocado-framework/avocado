import os
import unittest

from avocado.utils.software_manager import manager
from selftests.utils import BASEDIR, TestCaseTmpDir, skipUnlessPathExists


@skipUnlessPathExists('/usr/bin/cpio')
@skipUnlessPathExists('/usr/bin/rpm2cpio')
class SoftwareManager(TestCaseTmpDir):
    def setUp(self):
        super().setUp()
        # Functional tests are not being loaded properly. To be removed soon.
        assets_dir = os.path.join(BASEDIR, "selftests", ".data")
        self.rpm_path = os.path.join(assets_dir, "hello.rpm")
        self.deb_path = os.path.join(assets_dir, "hello.deb")

    def test_extract_from_rpm(self):
        mn = manager.SoftwareManager()
        result = mn.extract_from_package(self.rpm_path,
                                         self.tmpdir.name)
        self.assertEqual(self.tmpdir.name, result)

    def test_extract_from_deb(self):
        mn = manager.SoftwareManager()
        result = mn.extract_from_package(self.deb_path,
                                         self.tmpdir.name)
        self.assertEqual(self.tmpdir.name, result)

    def test_extract_permission(self):
        mn = manager.SoftwareManager()
        with self.assertRaises(NotImplementedError) as context:
            mn.extract_from_package('/dev/null', self.tmpdir.name)
        expected = 'No package manager supported was found for package '
        self.assertIn(expected, str(context.exception))


if __name__ == '__main__':
    unittest.main()
