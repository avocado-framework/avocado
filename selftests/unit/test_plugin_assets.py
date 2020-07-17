"""
Assets plugin unit tests
"""

import ast
import unittest
from unittest.mock import mock_open, patch

from avocado.plugins import assets


class AssetsPlugin(unittest.TestCase):
    """
    Unit tests for Assets Plugin
    """

    @patch('avocado.plugins.assets.FetchAssetHandler')
    def test_fetch_assets_sucess_fail(self, mocked_fetch_asset_handler):
        """
        Exercise a normal fetch for a success and a fail assets.
        """
        mocked_fetch_asset_handler.return_value.calls = [
            {'name': 'success.tar.gz',
             'locations': 'https://localhost/success.tar.gz',
             'asset_hash': None, 'algorithm': None, 'expire': None},
            {'name': 'fail.tar.gz',
             'locations': 'https://localhost/fail.tar.gz',
             'asset_hash': None, 'algorithm': None, 'expire': None},
        ]
        with patch('avocado.plugins.assets.Asset') as mocked_asset:
            mocked_asset.return_value.fetch.side_effect = [
                True,
                OSError('Failed to fetch fail.tar.gz.')]
            success, fail = assets.fetch_assets('test.py')
        expected_success = ['success.tar.gz']
        expected_fail_exception = OSError
        self.assertEqual(expected_success, success)
        self.assertTrue(isinstance(fail[0], expected_fail_exception))

    @patch('avocado.plugins.assets.FetchAssetHandler')
    def test_fetch_assets_sucess(self, mocked_fetch_asset_handler):
        """
        Exercise a normal fetch for a success asset.
        """
        mocked_fetch_asset_handler.return_value.calls = [
            {'name': 'success.tar.gz',
             'locations': 'https://localhost/success.tar.gz',
             'asset_hash': None, 'algorithm': None, 'expire': None},
        ]
        with patch('avocado.plugins.assets.Asset') as mocked_asset:
            mocked_asset.return_value.fetch.side_effect = [
                True]
            success, fail = assets.fetch_assets('test.py')
        expected_success = ['success.tar.gz']
        expected_fail = []
        self.assertEqual(expected_success, success)
        self.assertEqual(fail, expected_fail)

    @patch('avocado.plugins.assets.FetchAssetHandler')
    def test_fetch_assets_fail(self, mocked_fetch_asset_handler):
        """
        Exercise a normal fetch for a fail asset.
        """
        mocked_fetch_asset_handler.return_value.calls = [
            {'name': 'fail.tar.gz',
             'locations': 'https://localhost/fail.tar.gz',
             'asset_hash': None, 'algorithm': None, 'expire': None},
        ]
        with patch('avocado.plugins.assets.Asset') as mocked_asset:
            mocked_asset.return_value.fetch.side_effect = [
                OSError('Failed to fetch fail.tar.gz.')]
            success, fail = assets.fetch_assets('test.py')
        expected_success = []
        expected_fail_exception = OSError
        self.assertEqual(expected_success, success)
        self.assertTrue(isinstance(fail[0], expected_fail_exception))

    @patch('avocado.plugins.assets.FetchAssetHandler')
    def test_fetch_assets_empty_calls(self, mocked_fetch_asset_handler):
        """
        Exercise a normal fetch_assets for an empty `calls` variable.
        """
        mocked_fetch_asset_handler.return_value.calls = []
        success, fail = assets.fetch_assets('test.py')
        expected_success = []
        expected_fail = []
        self.assertEqual(expected_success, success)
        self.assertEqual(expected_fail, fail)


TEST_CLASS_SOURCE = r"""
from avocado import Test

class FetchAssets(Test):
    def test_fetch_assets(self):
        foo = "bar"
"""

NOT_TEST_CLASS_SOURCE = r"""
from avocado import Test

class FetchAssets:
    def test_fetch_assets(self):
        foo = "bar"
"""


class AssetsClass(unittest.TestCase):
    """
    Unit tests for Asset Class
    """

    @patch('avocado.plugins.assets.safeloader')
    def test_visit_classdef_valid_class(self, mocked_safeloader):
        """
        Make sure that current_klass is correctly assigned with a class name
        """
        mocked_safeloader.find_avocado_tests.return_value = [
            'FetchAssets'
        ]
        tree = ast.parse(TEST_CLASS_SOURCE)
        node = tree.body[1]
        with patch("builtins.open", mock_open(read_data=TEST_CLASS_SOURCE)):
            with patch.object(assets.ast, "parse"):
                with patch.object(assets.FetchAssetHandler, "visit"):
                    with patch.object(assets.FetchAssetHandler,
                                      "generic_visit"):
                        handler = assets.FetchAssetHandler("fake_file.py")
                        handler.visit_ClassDef(node)
                        self.assertEqual(handler.current_klass, 'FetchAssets')

    @patch('avocado.plugins.assets.safeloader')
    def test_visit_classdef_invalid_class(self, mocked_safeloader):
        """
        Make sure that current_klass is not assigned with a class name
        """
        mocked_safeloader.find_avocado_tests.return_value = [[]]
        tree = ast.parse(NOT_TEST_CLASS_SOURCE)
        node = tree.body[1]
        with patch("builtins.open", mock_open(read_data=NOT_TEST_CLASS_SOURCE)):
            with patch.object(assets.ast, "parse"):
                with patch.object(assets.FetchAssetHandler, "visit"):
                    with patch.object(assets.FetchAssetHandler,
                                      "generic_visit"):
                        handler = assets.FetchAssetHandler("fake_file.py")
                        handler.visit_ClassDef(node)
                        self.assertTrue((handler.current_klass is None))

    @patch('avocado.plugins.assets.safeloader')
    def test_visit_fuctiondef_valid_class(self, mocked_safeloader):
        """
        Make sure that current_klass is correctly assigned with a class name
        """
        mocked_safeloader.find_avocado_tests.return_value = [
            'FetchAssets'
        ]
        tree = ast.parse(TEST_CLASS_SOURCE)
        node_class = tree.body[1]
        node_function = tree.body[1].body[0]
        expected_method = "test_fetch_assets"
        with patch("builtins.open", mock_open(read_data=TEST_CLASS_SOURCE)):
            with patch.object(assets.ast, "parse"):
                with patch.object(assets.FetchAssetHandler, "visit"):
                    with patch.object(assets.FetchAssetHandler,
                                      "generic_visit"):
                        handler = assets.FetchAssetHandler("fake_file.py")
                        handler.visit_ClassDef(node_class)
                        handler.visit_FunctionDef(node_function)
                        self.assertEqual(handler.current_method, expected_method)

    @patch('avocado.plugins.assets.safeloader')
    def test_visit_fuctiondef_invalid_class(self, mocked_safeloader):
        """
        Make sure that current_klass is not assigned with a class name
        """
        mocked_safeloader.find_avocado_tests.return_value = [[]]
        tree = ast.parse(NOT_TEST_CLASS_SOURCE)
        node = tree.body[1].body[0]
        with patch("builtins.open", mock_open(read_data=NOT_TEST_CLASS_SOURCE)):
            with patch.object(assets.ast, "parse"):
                with patch.object(assets.FetchAssetHandler, "visit"):
                    with patch.object(assets.FetchAssetHandler,
                                      "generic_visit"):
                        handler = assets.FetchAssetHandler("fake_file.py")
                        handler.visit_FunctionDef(node)
                        self.assertTrue((handler.current_method is None))

    @patch('avocado.plugins.assets.safeloader')
    def test_visit_assign_valid_class_method(self, mocked_safeloader):
        """
        Make sure that current_klass is correctly assigned with a class name
        """
        mocked_safeloader.find_avocado_tests.return_value = [
            'FetchAssets'
        ]
        tree = ast.parse(TEST_CLASS_SOURCE)
        node_class = tree.body[1]
        node_function = tree.body[1].body[0]
        node_assign = tree.body[1].body[0].body[0]
        expected_assign = "bar"
        with patch("builtins.open", mock_open(read_data=TEST_CLASS_SOURCE)):
            with patch.object(assets.ast, "parse"):
                with patch.object(assets.FetchAssetHandler, "visit"):
                    with patch.object(assets.FetchAssetHandler,
                                      "generic_visit"):
                        handler = assets.FetchAssetHandler("fake_file.py")
                        handler.visit_ClassDef(node_class)
                        handler.visit_FunctionDef(node_function)
                        handler.visit_Assign(node_assign)
                        self.assertEqual(
                            (handler.asgmts[handler.current_klass]
                             [handler.current_method]['foo']),
                            expected_assign)

    @patch('avocado.plugins.assets.safeloader')
    def test_visit_assign_invalid_class_method(self, mocked_safeloader):
        """
        Make sure that current_klass is not assigned with a class name
        """
        mocked_safeloader.find_avocado_tests.return_value = [[]]
        tree = ast.parse(NOT_TEST_CLASS_SOURCE)
        node = tree.body[1].body[0].body[0]
        with patch("builtins.open", mock_open(read_data=NOT_TEST_CLASS_SOURCE)):
            with patch.object(assets.ast, "parse"):
                with patch.object(assets.FetchAssetHandler, "visit"):
                    with patch.object(assets.FetchAssetHandler,
                                      "generic_visit"):
                        handler = assets.FetchAssetHandler("fake_file.py")
                        handler.visit_Assign(node)
                        self.assertTrue((handler.current_method is None))


if __name__ == '__main__':
    unittest.main()
