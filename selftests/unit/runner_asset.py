import unittest

from avocado.core.nrunner.runnable import Runnable
from avocado.plugins.runners.asset import AssetRunner


class BasicTests(unittest.TestCase):
    """Basic unit tests for the AssetRunner class"""

    def test_no_kwargs(self):
        runnable = Runnable(kind="asset", uri=None)
        runner = AssetRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]["result"], "error")
        stderr = b"At least name should be passed as kwargs"
        self.assertIn(stderr, messages[-2]["log"])

    def test_wrong_name(self):
        runnable = Runnable(kind="asset", uri=None, **{"name": "foo"})
        runner = AssetRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]["result"], "error")
        stderr = b"Failed to fetch foo ("
        self.assertIn(stderr, messages[-2]["log"])


if __name__ == "__main__":
    unittest.main()
