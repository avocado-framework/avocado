import os
import shlex
import sys
import tempfile
import threading
import unittest
from contextlib import ExitStack
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from avocado.utils import process
from avocado.utils.filelock import FileLock
from selftests.utils import BASEDIR

RUNNER = f"{sys.executable} -m avocado.plugins.runners.asset"


class RunnableRun(unittest.TestCase):
    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory(prefix="avocado_runner_asset_")
        self.addCleanup(tmpdir.cleanup)
        self.asset_file = Path(tmpdir.name, "asset.txt")
        self.asset_file.write_bytes(b"Asset runner test fixture\n")

        cleanup = ExitStack()
        self.addCleanup(cleanup.close)
        cleanup.enter_context(
            FileLock(
                os.path.join(tempfile.gettempdir(), "avocado-runner-asset-http-18080"),
                timeout=60,
            )
        )
        handler = partial(SimpleHTTPRequestHandler, directory=tmpdir.name)
        server = HTTPServer(("127.0.0.1", 18080), handler)
        self.addCleanup(server.server_close)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        self.location = f"http://127.0.0.1:{server.server_port}/{self.asset_file.name}"

    def _assert_fetched(self, res):
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'time': ", res.stdout)
        self.assertIn(b"'log': b'File fetched at", res.stdout, res.stderr_text)
        self.assertIn(b"'result': 'pass'", res.stdout, res.stderr_text)
        self.assertEqual(res.exit_status, 0)

    def test_no_kwargs(self):
        res = process.run(f"{RUNNER} runnable-run -k asset", ignore_status=True)
        self.assertIn(b"'status': 'started'", res.stdout)
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"At least name should be passed as kwargs", res.stdout)
        self.assertIn(b"'time': ", res.stdout)
        self.assertEqual(res.exit_status, 0)

    def test_fetch(self):
        res = process.run(
            f"{RUNNER} runnable-run -k asset "
            f"name={self.asset_file.name} locations={self.location}",
            ignore_status=True,
            timeout=30,
            env={"no_proxy": "127.0.0.1", "NO_PROXY": "127.0.0.1"},
        )
        self._assert_fetched(res)

    def test_recipe(self):
        recipe = os.path.join(
            BASEDIR, "examples", "nrunner", "recipes", "runnable", "asset.json"
        )
        cmd = f"{RUNNER} runnable-run-recipe {shlex.quote(recipe)}"
        res = process.run(
            cmd,
            ignore_status=True,
            timeout=30,
            env={"no_proxy": "127.0.0.1", "NO_PROXY": "127.0.0.1"},
        )
        self._assert_fetched(res)


class TaskRun(unittest.TestCase):
    def test_no_kwargs(self):
        res = process.run(
            f"{RUNNER} task-run -i XXXreq-pacXXX -k asset", ignore_status=True
        )
        self.assertIn(b"'status': 'finished'", res.stdout)
        self.assertIn(b"'result': 'error'", res.stdout)
        self.assertIn(b"'id': 'XXXreq-pacXXX'", res.stdout)
        self.assertEqual(res.exit_status, 0)


if __name__ == "__main__":
    unittest.main()
