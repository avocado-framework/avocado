"""
Assets plugin functional tests
"""


import os
import tempfile
import unittest
import warnings

from avocado.core import exit_codes
from avocado.utils import process
from avocado.utils.asset import Asset
from selftests.utils import (AVOCADO, TestCaseTmpDir, get_temporary_config,
                             skipUnlessPathExists)

TEST_TEMPLATE = r"""
from avocado import Test

MODULE_CONST = "let's break the code"

def break_it():
    fake_test = Test()
    foo = "bar"
    bar = "foo"
    fake_test.fetch_asset(foo, bar)

class FetchAssets(Test):
    def test_fetch_assets(self):
{content}
"""

NOT_TEST_TEMPLATE = r"""
MODULE_CONST = "let's break the code"

def break_it():
    foo = "bar"
    bar = "foo"
    return foo, bar

class FetchAssets:
    def test_fetch_assets(self):
{content}
"""


class AssetsFetchSuccess(TestCaseTmpDir):
    """
    Assets fetch with success functional test class
    """

    def setUp(self):
        """
        Setup configuration file and folders
        """
        warnings.simplefilter("ignore", ResourceWarning)
        self.base_dir, self.mapping, self.config_file = get_temporary_config(self)
        asset_dir = os.path.join(self.mapping['cache_dir'], 'by_location',
                                 'a784600d3e01b346e8813bbd065d00048be8a482')
        os.makedirs(asset_dir)
        open(os.path.join(asset_dir, 'hello-2.9.tar.gz'), "w", encoding='utf-8').close()

    def test_asset_fetch_success(self):
        """
        Test ends successfully
        Asset is fetched from test source
        """
        fetch_content = r"""
        self.hello = self.fetch_asset(
            'hello-2.9.tar.gz',
            locations='https://mirrors.kernel.org/gnu/hello/hello-2.9.tar.gz')
        """
        test_content = TEST_TEMPLATE.format(content=fetch_content)
        test_file = tempfile.NamedTemporaryFile(suffix=".py", dir=self.base_dir.name, delete=False)
        test_file.write(test_content.encode())
        test_file.close()

        expected_output = (f"Fetching assets from {test_file.name}.\n"
                           f"  File hello-2.9.tar.gz fetched or "
                           f"already on cache.\n")
        expected_rc = exit_codes.AVOCADO_ALL_OK

        cmd_line = (f"{AVOCADO} --config {self.config_file.name} "
                    f"assets fetch {test_file.name} ")
        result = process.run(cmd_line)
        os.remove(test_file.name)

        self.assertEqual(expected_rc, result.exit_status)
        self.assertIn(expected_output, result.stdout_text)

    def test_asset_register_by_name_fail(self):
        """Test register command failure."""
        url = "https://urlnotfound"
        config = self.config_file.name
        cmd_line = f"{AVOCADO} --config {config} assets register foo {url}"
        result = process.run(cmd_line, ignore_status=True)

        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
        self.assertIn("Failed to fetch",
                      result.stderr_text)

    @skipUnlessPathExists('/etc/hosts')
    def test_asset_register_by_name_success(self):
        """Test register command success."""
        url = "/etc/hosts"
        config = self.config_file.name
        cmd_line = f"{AVOCADO} --config {config} assets register hosts {url}"
        result = process.run(cmd_line)

        self.assertIn("Now you can reference it by name hosts",
                      result.stdout_text)

    def test_asset_purge(self):
        """Make sure that we can remove a asset from cache."""
        # creates a single byte asset
        asset_file = tempfile.NamedTemporaryFile(dir=self.base_dir.name, delete=False)
        asset_file.write(b'\xff')
        asset_file.close()

        config = self.config_file.name
        url = asset_file.name
        name = "should-be-removed"
        cmd_line = f"{AVOCADO} --config {config} assets register {name} {url}"
        result = process.run(cmd_line)
        self.assertIn(f"Now you can reference it by name {name}",
                      result.stdout_text)

        cmd_line = (f"{AVOCADO} --config {config} assets purge "
                    f"--by-size-filter '==1'")
        process.run(cmd_line)

        cmd_line = f"{AVOCADO} --config {config} assets list"
        result = process.run(cmd_line)
        self.assertNotIn(name, result.stdout_text)

    @skipUnlessPathExists('/etc/hosts')
    def test_asset_list(self):
        """Make sure that we have a list working properly."""
        url = "/etc/hosts"
        config = self.config_file.name
        name = "should-be-part-of-list"
        cmd_line = f"{AVOCADO} --config {config} assets register {name} {url}"
        result = process.run(cmd_line)
        self.assertIn(f"Now you can reference it by name {name}",
                      result.stdout_text)
        cmd_line = f"{AVOCADO} --config {config} assets list"
        result = process.run(cmd_line)
        self.assertIn(name, result.stdout_text)

    def test_asset_purge_by_overall_cache_size(self):
        """Make sure that we can set cache limits."""
        # creates a single byte asset
        asset_file = tempfile.NamedTemporaryFile(dir=self.base_dir.name, delete=False)
        asset_file.write(b'\xff')
        asset_file.close()

        config = self.config_file.name
        url = asset_file.name
        name = "should-be-removed"
        cmd_line = f"{AVOCADO} --config {config} assets register {name} {url}"
        result = process.run(cmd_line)
        self.assertIn(f"Now you can reference it by name {name}",
                      result.stdout_text)

        cmd_line = (f"{AVOCADO} --config {config} assets purge "
                    f"--by-overall-limit 2")
        process.run(cmd_line)

        cmd_line = f"{AVOCADO} --config {config} assets list"
        result = process.run(cmd_line)
        self.assertIn(name, result.stdout_text)

        # Double check that the sum of assets is not bigger than 2bytes
        size_sum = 0
        for asset in Asset.get_all_assets([self.mapping['cache_dir']]):
            size_sum += os.stat(asset).st_size
        self.assertLessEqual(size_sum, 2)

    def tearDown(self):
        self.base_dir.cleanup()


class AssetsPlugin(unittest.TestCase):
    """
    Main assets plugin functional test class
    """

    def setUp(self):
        """
        Setup configuration file and folders
        """
        warnings.simplefilter("ignore", ResourceWarning)
        self.base_dir, self.mapping, self.config_file = get_temporary_config(self)

    def test_asset_fetch(self):
        """
        Command ends with warning
        Exercise `avocado assets fetch` without any argument
        """
        expected_stderr = "avocado assets fetch: error: the following" \
            " arguments are required: AVOCADO_INSTRUMENTED\n"
        expected_rc = exit_codes.AVOCADO_FAIL

        cmd_line = f"{AVOCADO} --config {self.config_file.name} assets fetch"
        result = process.run(cmd_line, ignore_status=True)

        self.assertEqual(expected_rc, result.exit_status)
        self.assertIn(expected_stderr, result.stderr_text)

    def test_asset_fetch_unsupported_class(self):
        """
        Test ends with warning
        No supported class into the test file
        """
        fetch_content = r"""
        self.hello = self.fetch_asset(
            'hello-2.9.tar.gz',
            locations='https://mirrors.kernel.org/gnu/hello/hello-2.9.tar.gz')
        """
        test_content = NOT_TEST_TEMPLATE.format(content=fetch_content)
        test_file = tempfile.NamedTemporaryFile(suffix=".py", dir=self.base_dir.name, delete=False)
        test_file.write(test_content.encode())
        test_file.close()

        expected_stdout = f"Fetching assets from {test_file.name}.\n"
        expected_rc = exit_codes.AVOCADO_ALL_OK

        cmd_line = (f"{AVOCADO} --config {self.config_file.name} "
                    f"assets fetch {test_file.name} ")
        result = process.run(cmd_line, ignore_status=True)
        os.remove(test_file.name)

        self.assertEqual(expected_rc, result.exit_status)
        self.assertIn(expected_stdout, result.stdout_text)

    def test_asset_fetch_unsupported_file(self):
        """
        Test ends with warning
        No supported test file
        """
        fetch_content = r"""
        self.hello = self.fetch_asset(
            'hello-2.9.tar.gz',
            locations='https://mirrors.kernel.org/gnu/hello/hello-2.9.tar.gz')
        """
        test_content = TEST_TEMPLATE.format(content=fetch_content)
        test_file = tempfile.NamedTemporaryFile(suffix=".c",  dir=self.base_dir.name, delete=False)
        test_file.write(test_content.encode())
        test_file.close()

        expected_stderr = (f"No such file or file not supported: "
                           f"{test_file.name}\n")
        expected_rc = exit_codes.AVOCADO_FAIL

        cmd_line = (f"{AVOCADO} --config {self.config_file.name} "
                    f"assets fetch {test_file.name} ")
        result = process.run(cmd_line, ignore_status=True)
        os.remove(test_file.name)

        self.assertEqual(expected_rc, result.exit_status)
        self.assertIn(expected_stderr, result.stderr_text)

    def test_asset_fetch_invalid_url(self):
        """
        Test ends with warning
        Problems while fetching asset from test source
        """
        fetch_content = r"""
        self.hello = self.fetch_asset(
            'hello-2.9.tar.gz',
            locations='http://localhost/hello-2.9.tar.gz')
        """
        test_content = TEST_TEMPLATE.format(content=fetch_content)
        test_file = tempfile.NamedTemporaryFile(suffix=".py", dir=self.base_dir.name, delete=False)
        test_file.write(test_content.encode())
        test_file.close()

        expected_stderr = "Failed to fetch hello-2.9.tar.gz"
        expected_rc = exit_codes.AVOCADO_FAIL

        cmd_line = (f"{AVOCADO} --config {self.config_file.name} "
                    f"assets fetch {test_file.name} ")
        result = process.run(cmd_line, ignore_status=True)
        os.remove(test_file.name)

        self.assertEqual(expected_rc, result.exit_status)
        self.assertIn(expected_stderr, result.stderr_text)

    def test_asset_fetch_ignore_errors(self):
        """
        Test ends with warning but success error code
        Problems while fetching asset from test source
        """
        fetch_content = r"""
        self.hello = self.fetch_asset(
            'hello-2.9.tar.gz',
            locations='http://localhost/hello-2.9.tar.gz')
        """
        test_content = TEST_TEMPLATE.format(content=fetch_content)
        test_file = tempfile.NamedTemporaryFile(suffix=".py", dir=self.base_dir.name, delete=False)
        test_file.write(test_content.encode())
        test_file.close()

        expected_stderr = "Failed to fetch hello-2.9.tar.gz"
        expected_rc = exit_codes.AVOCADO_ALL_OK

        cmd_line = (f"{AVOCADO} --config {self.config_file.name} "
                    f"assets fetch --ignore-errors {test_file.name} ")
        result = process.run(cmd_line, ignore_status=True)
        os.remove(test_file.name)

        self.assertEqual(expected_rc, result.exit_status)
        self.assertIn(expected_stderr, result.stderr_text)

    def test_asset_purge_by_days(self):
        """Make sure that we can remove assets by days."""
        # creates a single byte asset
        asset_file = tempfile.NamedTemporaryFile(dir=self.base_dir.name, delete=False)
        asset_file.write(b'\xff')
        asset_file.close()

        config = self.config_file.name
        url = asset_file.name
        name = "should-be-removed"
        cmd_line = f"{AVOCADO} --config {config} assets register {name} {url}"
        result = process.run(cmd_line)
        self.assertIn(f"Now you can reference it by name {name}",
                      result.stdout_text)

        cmd_line = f"{AVOCADO} --config {config} assets list"
        result = process.run(cmd_line)
        self.assertIn(name, result.stdout_text)

        cmd_line = f"{AVOCADO} --config {config} assets purge --by-days 0"
        process.run(cmd_line)

        cmd_line = f"{AVOCADO} --config {config} assets list"
        result = process.run(cmd_line)
        self.assertNotIn(name, result.stdout_text)

    def tearDown(self):
        os.remove(self.config_file.name)
        self.base_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
