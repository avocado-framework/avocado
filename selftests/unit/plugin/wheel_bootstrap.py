import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from avocado.core.spawners import wheel_bootstrap
from avocado.core.spawners.wheel_bootstrap import (
    CONTAINER_SITE,
    BootstrapMount,
    prepare_bootstrap,
    wheel_filename,
)
from selftests.utils import BASEDIR


class WheelBootstrap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._wheels_dir = tempfile.TemporaryDirectory(prefix="avocado_wheel_bs_")
        cls.wheel = wheel_bootstrap.build_wheel_from_source(
            BASEDIR, cls._wheels_dir.name
        )

    @classmethod
    def tearDownClass(cls):
        cls._wheels_dir.cleanup()

    def test_wheel_is_universal(self):
        self.assertTrue(self.wheel.endswith("-py3-none-any.whl"))
        self.assertEqual(os.path.basename(self.wheel), wheel_filename())

    def test_prepare_unpacked_wheel_is_importable(self):
        with tempfile.TemporaryDirectory(prefix="avocado_wheel_cache_") as cache:
            mount = prepare_bootstrap(url=f"file://{self.wheel}", cache_dirs=[cache])
            self.assertIsInstance(mount, BootstrapMount)
            self.assertEqual(mount.container_path, CONTAINER_SITE)
            self.assertEqual(mount.pythonpath, CONTAINER_SITE)
            self.assertTrue(os.path.isdir(mount.host_path))
            self.assertTrue(os.path.isdir(os.path.join(mount.host_path, "avocado")))

            env = os.environ.copy()
            env["PYTHONPATH"] = mount.host_path
            probe = (
                "import avocado; "
                "from avocado.plugins.runners.exec_test import ExecTestRunner; "
                "print(avocado.__file__)"
            )
            result = subprocess.run(
                [sys.executable, "-c", probe],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertIn("avocado", result.stdout)

    def test_legacy_egg_keeps_zip_on_pythonpath(self):
        with tempfile.TemporaryDirectory(prefix="avocado_egg_") as tmp:
            egg = os.path.join(tmp, "avocado_framework-113.0-py3.12.egg")
            with zipfile.ZipFile(egg, "w") as archive:
                archive.writestr("dummy", "not-a-real-egg")
            cache = os.path.join(tmp, "cache")
            os.mkdir(cache)
            mount = prepare_bootstrap(url=f"file://{egg}", cache_dirs=[cache])
        self.assertTrue(mount.host_path.endswith(".egg"))
        self.assertTrue(mount.pythonpath.endswith(".egg"))
        self.assertNotEqual(mount.container_path, CONTAINER_SITE)

    def test_explicit_unpacked_directory(self):
        with tempfile.TemporaryDirectory(prefix="avocado_site_") as tmp:
            site = Path(tmp) / "site"
            site.mkdir()
            (site / "avocado").mkdir()
            mount = prepare_bootstrap(url=f"file://{site}", cache_dirs=[tmp])
            self.assertEqual(os.path.realpath(mount.host_path), os.path.realpath(site))
            self.assertEqual(mount.pythonpath, CONTAINER_SITE)

    def test_default_builds_from_source_tree(self):
        with tempfile.TemporaryDirectory(prefix="avocado_wheel_src_") as cache:
            mount = prepare_bootstrap(cache_dirs=[cache])
            self.assertTrue(os.path.isdir(os.path.join(mount.host_path, "avocado")))
            env = os.environ.copy()
            env["PYTHONPATH"] = mount.host_path
            result = subprocess.run(
                [sys.executable, "-m", "avocado.plugins.runners.exec_test", "--help"],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
        self.assertIn("task-run", result.stdout + result.stderr)
