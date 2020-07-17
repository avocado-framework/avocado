"""
Assets plugin functional tests
"""


import os
import tempfile
import unittest
import warnings

from avocado.core import exit_codes
from avocado.utils import process

from .. import AVOCADO, get_temporary_config

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


class AssetsFetchSuccess(unittest.TestCase):
    """
    Assets fetch with success functional test class
    """

    def setUp(self):
        """
        Setup configuration file and folders
        """
        warnings.simplefilter("ignore", ResourceWarning)
        self.base_dir, self.mapping, self.config_file = get_temporary_config(
            __name__, self, 'setUp')
        asset_dir = os.path.join(self.mapping['cache_dir'], 'by_location',
                                 'a784600d3e01b346e8813bbd065d00048be8a482')
        os.makedirs(asset_dir)
        open(os.path.join(asset_dir, 'hello-2.9.tar.gz'), "w").close()

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
        test_file = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        test_file.write(test_content.encode())
        test_file.close()

        expected_output = "Fetching assets from %s.\n" \
            "  File hello-2.9.tar.gz fetched or already on cache.\n" \
            % test_file.name
        expected_rc = exit_codes.AVOCADO_ALL_OK

        cmd_line = "%s --config %s assets fetch %s " % (AVOCADO,
                                                        self.config_file.name,
                                                        test_file.name)
        result = process.run(cmd_line)
        os.remove(test_file.name)

        self.assertEqual(expected_rc, result.exit_status)
        self.assertIn(expected_output, result.stdout_text)

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
        self.base_dir, self.mapping, self.config_file = get_temporary_config(
            __name__, self, 'setUp')

    def test_asset_fetch(self):
        """
        Command ends with warning
        Exercise `avocado assets fetch` without any argument
        """
        expected_stderr = "avocado assets fetch: error: the following" \
            " arguments are required: AVOCADO_INSTRUMENTED\n"
        expected_rc = exit_codes.AVOCADO_FAIL

        cmd_line = "%s --config %s assets fetch" % (AVOCADO,
                                                    self.config_file.name)
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
        test_file = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        test_file.write(test_content.encode())
        test_file.close()

        expected_stdout = "Fetching assets from %s.\n" % test_file.name
        expected_rc = exit_codes.AVOCADO_ALL_OK

        cmd_line = "%s --config %s assets fetch %s " % (AVOCADO,
                                                        self.config_file.name,
                                                        test_file.name)
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
        test_file = tempfile.NamedTemporaryFile(suffix=".c", delete=False)
        test_file.write(test_content.encode())
        test_file.close()

        expected_stderr = "No such file or file not supported: %s\n" \
            % test_file.name
        expected_rc = exit_codes.AVOCADO_FAIL

        cmd_line = "%s --config %s assets fetch %s " % (AVOCADO,
                                                        self.config_file.name,
                                                        test_file.name)
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
        test_file = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        test_file.write(test_content.encode())
        test_file.close()

        expected_stderr = "Failed to fetch hello-2.9.tar.gz.\n"
        expected_rc = exit_codes.AVOCADO_FAIL

        cmd_line = "%s --config %s assets fetch %s " % (AVOCADO,
                                                        self.config_file.name,
                                                        test_file.name)
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
        test_file = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        test_file.write(test_content.encode())
        test_file.close()

        expected_stderr = "Failed to fetch hello-2.9.tar.gz.\n"
        expected_rc = exit_codes.AVOCADO_ALL_OK

        cmd_line = "%s --config %s assets fetch --ignore-errors %s " % (
            AVOCADO,
            self.config_file.name,
            test_file.name)
        result = process.run(cmd_line, ignore_status=True)
        os.remove(test_file.name)

        self.assertEqual(expected_rc, result.exit_status)
        self.assertIn(expected_stderr, result.stderr_text)

    def tearDown(self):
        os.remove(self.config_file.name)
        self.base_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
