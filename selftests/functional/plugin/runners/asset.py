import os

from avocado.core.nrunner.runnable import Runnable
from avocado.plugins.runners.asset import AssetRunner
from selftests.utils import TestCaseTmpDir


class AssetRunnerTest(TestCaseTmpDir):
    def setUp(self):
        super().setUp()
        self.cache_dir = os.path.join(self.tmpdir.name, "cache")
        self.asset_file = os.path.join(self.tmpdir.name, "asset.txt")
        with open(self.asset_file, "wb") as asset:
            asset.write(b"avocado!\n")

    def test_success_fetch(self):
        runnable = Runnable(
            kind="asset",
            uri=None,
            **{"name": f"file://{self.asset_file}"},
            config={"datadir.paths.cache_dirs": self.cache_dir},
        )
        runner = AssetRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]["result"], "pass")
        stdout = b"File fetched at "
        self.assertIn(stdout, messages[-3]["log"])

    def test_fail_fetch(self):
        runnable = Runnable(
            kind="asset",
            uri=None,
            **{"name": "asset.txt"},
            config={"datadir.paths.cache_dirs": self.cache_dir},
        )
        runner = AssetRunner()
        status = runner.run(runnable)
        messages = []
        while True:
            try:
                messages.append(next(status))
            except StopIteration:
                break
        self.assertEqual(messages[-1]["result"], "error")
        stderr = b"Failed to fetch asset.txt"
        self.assertIn(stderr, messages[-2]["log"])
