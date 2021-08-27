"""
Functional tests for fetch_asset core test method
"""


import os
import tempfile
import unittest
import warnings

from avocado.core import exit_codes
from avocado.utils import process
from selftests.utils import AVOCADO, get_temporary_config

TEST_TEMPLATE = r"""
from avocado import Test

class FetchAsset(Test):
    def test_fetch_asset(self):
{content}
"""


class FetchAsset(unittest.TestCase):
    """
    Functional test class for fetch_asset core method
    """

    def setUp(self):
        """
        Setup configuration file and folders
        """
        warnings.simplefilter("ignore", ResourceWarning)
        self.base_dir, self.mapping, self.config_file = get_temporary_config(self)

        self.asset_dir = os.path.join(self.mapping['cache_dir'],
                                      'by_location',
                                      'foo')
        os.makedirs(self.asset_dir)

    def test_asset_fetch_find_success(self):
        """
        Test ends successfully
        Asset is found in the cache
        """
        assetname = 'foo.tgz'
        localpath = os.path.join(self.asset_dir, assetname)
        with open(localpath, 'w') as f:
            f.write('Test!')
        url = 'file://%s' % localpath
        fetch_content = r"""
        foo = self.fetch_asset(
            '%s',
            locations='%s',
            find_only=True)
        print(foo)
        """ % (assetname, url)
        test_content = TEST_TEMPLATE.format(content=fetch_content)
        test_file = tempfile.NamedTemporaryFile(suffix=".py", dir=self.base_dir.name, delete=False)
        test_file.write(test_content.encode())
        test_file.close()

        expected_rc = exit_codes.AVOCADO_ALL_OK
        cmd_line = ("%s --config %s run "
                    "--test-runner=runner "
                    "%s" % (AVOCADO,
                            self.config_file.name,
                            test_file.name))
        result = process.run(cmd_line)
        os.remove(localpath)
        self.assertEqual(expected_rc, result.exit_status)

    def test_asset_fetch_find_fail(self):
        """
        Test fails
        Asset is not found in the cache
        """
        fake_assetname = 'fake_foo.tgz'
        localpath = os.path.join(self.asset_dir, fake_assetname)
        fake_url = 'file://%s' % localpath
        fetch_content = r"""
        foo = self.fetch_asset(
            '%s',
            locations='%s',
            find_only=True)
        if foo is None:
            raise OSError('Asset not found')
        """ % (fake_assetname, fake_url)
        test_content = TEST_TEMPLATE.format(content=fetch_content)
        test_file = tempfile.NamedTemporaryFile(suffix=".py", dir=self.base_dir.name, delete=False)
        test_file.write(test_content.encode())
        test_file.close()

        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        expected_stdout = "not found in the cache"

        cmd_line = ("%s --config %s run "
                    "--test-runner=runner "
                    "%s" % (AVOCADO,
                            self.config_file.name,
                            test_file.name))

        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(expected_rc, result.exit_status)
        self.assertIn(expected_stdout, result.stdout_text)

    def test_asset_fetch_find_fail_cancel(self):
        """
        Test cancels
        Asset is not found in the cache
        """
        fake_assetname = 'fake_foo.tgz'
        localpath = os.path.join(self.asset_dir, fake_assetname)
        fake_url = 'file://%s' % localpath
        fetch_content = r"""
        foo = self.fetch_asset(
            '%s',
            locations='%s',
            find_only=True,
            cancel_on_missing=True)
        """ % (fake_assetname, fake_url)
        test_content = TEST_TEMPLATE.format(content=fetch_content)
        test_file = tempfile.NamedTemporaryFile(suffix=".py", dir=self.base_dir.name, delete=False)
        test_file.write(test_content.encode())
        test_file.close()

        expected_rc = exit_codes.AVOCADO_ALL_OK
        expected_stdout = "Missing asset"

        cmd_line = ("%s --config %s run "
                    "--test-runner=runner "
                    "%s" % (AVOCADO,
                            self.config_file.name,
                            test_file.name))

        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(expected_rc, result.exit_status)
        self.assertIn(expected_stdout, result.stdout_text)

    def test_asset_fetch_cancel(self):
        """
        Test cancels
        Failed to fetch asset
        """
        fake_assetname = 'fake_foo.tgz'
        localpath = os.path.join(self.asset_dir, fake_assetname)
        fake_url = 'file://%s' % localpath
        fetch_content = r"""
        foo = self.fetch_asset(
            '%s',
            locations='%s',
            cancel_on_missing=True)
        """ % (fake_assetname, fake_url)
        test_content = TEST_TEMPLATE.format(content=fetch_content)
        test_file = tempfile.NamedTemporaryFile(suffix=".py", dir=self.base_dir.name, delete=False)
        test_file.write(test_content.encode())
        test_file.close()

        expected_rc = exit_codes.AVOCADO_ALL_OK
        expected_stdout = "Missing asset"

        cmd_line = ("%s --config %s run "
                    "--test-runner=runner "
                    "%s " % (AVOCADO,
                             self.config_file.name,
                             test_file.name))

        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(expected_rc, result.exit_status)
        self.assertIn(expected_stdout, result.stdout_text)

    def tearDown(self):
        os.remove(self.config_file.name)
        self.base_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
