import unittest
from unittest.mock import patch

from avocado.core.nrunner.runnable import Runnable
from avocado.plugins.runners.package import PackageRunner


class BasicTests(unittest.TestCase):
    """Basic unit tests for the PackageRunner class"""

    def test_no_kwargs(self):
        runnable = Runnable(kind='package', uri=None)
        runner = PackageRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        result = 'error'
        self.assertIn(result, messages[-1]['result'])
        stderr = b'Package name should be passed as kwargs'
        self.assertIn(stderr, messages[-2]['log'])

    def test_wrong_action(self):
        runnable = Runnable(kind='package', uri=None,
                            **{'action': 'foo'})
        runner = PackageRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        result = 'error'
        self.assertIn(result, messages[-1]['result'])
        stderr = b"Invalid action foo. Use one of 'install', 'check' or 'remove'"
        self.assertIn(stderr, messages[-2]['log'])


class ActionTests(unittest.TestCase):
    """Unit tests for the actions on PackageRunner class"""

    def setUp(self):
        """Mock SoftwareManager"""

        self.sm_patcher = patch(
            'avocado.plugins.runners.package.SoftwareManager',
            autospec=True)
        self.mock_sm = self.sm_patcher.start()
        self.addCleanup(self.sm_patcher.stop)

    def test_success_install(self):

        self.mock_sm.return_value.check_installed = lambda check_installed: False
        self.mock_sm.return_value.install = lambda install: True
        runnable = Runnable(kind='package', uri=None,
                            **{'action': 'install', 'name': 'foo'})
        runner = PackageRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]['result'], 'pass')
        stdout = b'Package(s) foo installed successfully'
        self.assertIn(stdout, messages[-3]['log'])

    def test_already_installed(self):

        self.mock_sm.return_value.check_installed = lambda check_installed: True
        runnable = Runnable(kind='package', uri=None,
                            **{'action': 'install', 'name': 'foo'})
        runner = PackageRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]['result'], 'pass')
        stdout = b'Package foo already installed'
        self.assertIn(stdout, messages[-3]['log'])

    def test_fail_install(self):

        self.mock_sm.return_value.check_installed = lambda check_installed: False
        self.mock_sm.return_value.install = lambda install: False
        runnable = Runnable(kind='package', uri=None,
                            **{'action': 'install', 'name': 'foo'})
        runner = PackageRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]['result'], 'error')
        stderr = b'Failed to install foo.'
        self.assertIn(stderr, messages[-2]['log'])

    def test_success_remove(self):

        self.mock_sm.return_value.check_installed = lambda check_installed: True
        self.mock_sm.return_value.remove = lambda remove: True
        runnable = Runnable(kind='package', uri=None,
                            **{'action': 'remove', 'name': 'foo'})
        runner = PackageRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]['result'], 'pass')
        stdout = b'Package(s) foo removed successfully'
        self.assertIn(stdout, messages[-3]['log'])

    def test_not_installed(self):

        self.mock_sm.return_value.check_installed = lambda check_installed: False
        runnable = Runnable(kind='package', uri=None,
                            **{'action': 'remove', 'name': 'foo'})
        runner = PackageRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]['result'], 'pass')
        stdout = b'Package foo not installed'
        self.assertIn(stdout, messages[-3]['log'])

    def test_fail_remove(self):

        self.mock_sm.return_value.check_installed = lambda check_installed: True
        self.mock_sm.return_value.remove = lambda remove: False
        runnable = Runnable(kind='package', uri=None,
                            **{'action': 'remove', 'name': 'foo'})
        runner = PackageRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]['result'], 'error')
        stderr = b'Failed to remove foo.'
        self.assertIn(stderr, messages[-2]['log'])

    def test_success_check(self):

        self.mock_sm.return_value.check_installed = lambda check_installed: True
        runnable = Runnable(kind='package', uri=None,
                            **{'action': 'check', 'name': 'foo'})
        runner = PackageRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]['result'], 'pass')
        stdout = b'Package foo already installed'
        self.assertIn(stdout, messages[-3]['log'])

    def test_fail_check(self):

        self.mock_sm.return_value.check_installed = lambda check_installed: False
        runnable = Runnable(kind='package', uri=None,
                            **{'action': 'check', 'name': 'foo'})
        runner = PackageRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]['result'], 'error')
        stderr = b'Package foo not installed'
        self.assertIn(stderr, messages[-2]['log'])


if __name__ == '__main__':
    unittest.main()
