import unittest
from unittest.mock import patch

from avocado.core.nrunner import Runnable
from avocado.core.runners.requirement_asset import RequirementAssetRunner


class BasicTests(unittest.TestCase):
    """Basic unit tests for the RequirementAssetRunner class"""

    def test_no_kwargs(self):
        runnable = Runnable(kind='requirement-asset', uri=None)
        runner = RequirementAssetRunner(runnable)
        status = runner.run()
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        result = 'error'
        self.assertIn(result, messages[-1]['result'])
        stderr = b'At least name should be passed as kwargs'
        self.assertIn(stderr, messages[-2]['log'])

    def test_wrong_name(self):
        runnable = Runnable(kind='requirement-asset', uri=None,
                            **{'name': 'foo'})
        runner = RequirementAssetRunner(runnable)
        status = runner.run()
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        result = 'error'
        self.assertIn(result, messages[-1]['result'])
        stderr = b"Failed to fetch foo ("
        self.assertIn(stderr, messages[-2]['log'])


class FetchTests(unittest.TestCase):
    """Unit tests for the actions on RequirementPackageRunner class"""

    def setUp(self):
        """Mock SoftwareManager"""

        self.sm_patcher = patch(
            'avocado.core.runners.requirement_asset.Asset',
            autospec=True)
        self.mock_sm = self.sm_patcher.start()
        self.addCleanup(self.sm_patcher.stop)

    def test_success_fetch(self):

        self.mock_sm.return_value.fetch.return_value = '/tmp/asset.txt'
        runnable = Runnable(kind='requirement-asset', uri=None,
                            **{'name': 'asset.txt'})
        runner = RequirementAssetRunner(runnable)
        status = runner.run()
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        result = 'pass'
        self.assertIn(result, messages[-1]['result'])
        stdout = b'File fetched at /tmp/asset.txt'
        self.assertIn(stdout, messages[-3]['log'])

    def test_fail_fetch(self):

        self.mock_sm.return_value.fetch = lambda: (_ for _ in ()).throw(
            OSError('Failed to fetch asset.txt'))
        runnable = Runnable(kind='requirement-asset', uri=None,
                            **{'name': 'asset.txt'})
        runner = RequirementAssetRunner(runnable)
        status = runner.run()
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        result = 'error'
        self.assertIn(result, messages[-1]['result'])
        stderr = b'Failed to fetch asset.txt'
        self.assertIn(stderr, messages[-2]['log'])


if __name__ == '__main__':
    unittest.main()
