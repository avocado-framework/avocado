import unittest
from unittest.mock import patch

from avocado.core.nrunner.runnable import Runnable
from avocado.plugins.runners.asset import AssetRunner


class BasicTests(unittest.TestCase):
    """Basic unit tests for the AssetRunner class"""

    def test_no_kwargs(self):
        runnable = Runnable(kind='asset', uri=None)
        runner = AssetRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]['result'], 'error')
        stderr = b'At least name should be passed as kwargs'
        self.assertIn(stderr, messages[-2]['log'])

    def test_wrong_name(self):
        runnable = Runnable(kind='asset', uri=None,
                            **{'name': 'foo'})
        runner = AssetRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]['result'], 'error')
        stderr = b"Failed to fetch foo ("
        self.assertIn(stderr, messages[-2]['log'])


class FetchTests(unittest.TestCase):
    """Unit tests for the actions on RequirementPackageRunner class"""

    def setUp(self):
        """Mock SoftwareManager"""

        self.asset_patcher = patch(
            'avocado.plugins.runners.asset.Asset',
            autospec=True)
        self.mock_asset = self.asset_patcher.start()
        self.addCleanup(self.asset_patcher.stop)

    def test_success_fetch(self):

        self.mock_asset.return_value.fetch.return_value = '/tmp/asset.txt'
        runnable = Runnable(kind='asset', uri=None,
                            **{'name': 'asset.txt'})
        runner = AssetRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]['result'], 'pass')
        stdout = b'File fetched at /tmp/asset.txt'
        self.assertIn(stdout, messages[-3]['log'])

    def test_fail_fetch(self):

        self.mock_asset.return_value.fetch = lambda: (_ for _ in ()).throw(
            OSError('Failed to fetch asset.txt'))
        runnable = Runnable(kind='asset', uri=None,
                            **{'name': 'asset.txt'})
        runner = AssetRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]['result'], 'error')
        stderr = b'Failed to fetch asset.txt'
        self.assertIn(stderr, messages[-2]['log'])


if __name__ == '__main__':
    unittest.main()
