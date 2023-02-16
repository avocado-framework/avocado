import asyncio
import os
import sys
from unittest import mock

from avocado import Test, skipIf
from avocado.core.job import Job
from avocado.plugins.spawners import lxc
from avocado.plugins.spawners.lxc import LXCSpawner
from selftests.utils import BASEDIR

LXC_BACKEND = mock.MagicMock()


def incompatible_python_version():
    return sys.version_info.major == 3 and sys.version_info.minor <= 7


@skipIf(incompatible_python_version(), "Not compatible with Python under 3.7.0")
@mock.patch("avocado.plugins.spawners.lxc.lxc", LXC_BACKEND)
class LXCSpawnerTest(Test):
    def setUp(self):
        config = {
            "run.results_dir": self.workdir,
            "resolver.references": [
                os.path.join(BASEDIR, "examples", "tests", "gendata.py")
            ],
            "run.spawner": "lxc",
            "spawner.lxc.slots": ["c1", "c2", "c3"],
        }

        lxc.LXC_AVAILABLE = True
        with Job.from_config(job_config=config) as job:
            self.spawner = LXCSpawner(config, job)
            LXCSpawner.slots_cache = {}

    def tearDown(self):
        LXC_BACKEND.reset_mock()

    def test_slots_cache_custom(self):
        """Checks if custom (scheduler predefined) slots could be used from cache."""
        runtime_task = mock.MagicMock()
        runtime_task.spawner_handle = "c100"

        to_spawn = self.spawner.spawn_task(runtime_task)
        with mock.patch.object(
            LXCSpawner, "run_container_cmd", return_value=(0, "", "")
        ):
            with mock.patch.object(
                LXCSpawner, "run_container_cmd_async", return_value=(0, "", "")
            ):
                asyncio.run(to_spawn)

        LXC_BACKEND.Container.assert_called_with("c100")
        self.assertEqual(
            LXCSpawner.slots_cache,
            {"c1": False, "c2": False, "c3": False, "c100": False},
        )

    def test_slots_cache_free(self):
        """Checks if free slots could be used from cache."""
        runtime_task = mock.MagicMock()
        runtime_task.spawner_handle = None

        to_spawn = self.spawner.spawn_task(runtime_task)
        with mock.patch.object(
            LXCSpawner, "run_container_cmd", return_value=(0, "", "")
        ):
            with mock.patch.object(
                LXCSpawner, "run_container_cmd_async", return_value=(0, "", "")
            ):
                asyncio.run(to_spawn)

        LXC_BACKEND.Container.assert_called_with("c1")
        self.assertEqual(
            LXCSpawner.slots_cache, {"c1": False, "c2": False, "c3": False}
        )

    def test_slots_cache_free_next(self):
        """Checks if free slots could be used from cache with some slots occupied."""
        runtime_task = mock.MagicMock()
        runtime_task.spawner_handle = None
        LXCSpawner.slots_cache = {"c1": True, "c2": False}

        to_spawn = self.spawner.spawn_task(runtime_task)
        with mock.patch.object(
            LXCSpawner, "run_container_cmd", return_value=(0, "", "")
        ):
            with mock.patch.object(
                LXCSpawner, "run_container_cmd_async", return_value=(0, "", "")
            ):
                asyncio.run(to_spawn)

        LXC_BACKEND.Container.assert_called_with("c2")
        # c1 remains occupied throughout this test run
        self.assertEqual(LXCSpawner.slots_cache, {"c1": True, "c2": False})

    def test_slots_cache_full(self):
        """Checks if free slots could be used from cache with some slots occupied."""
        runtime_task = mock.MagicMock()
        runtime_task.spawner_handle = None
        LXCSpawner.slots_cache = {"c1": True}

        to_spawn = self.spawner.spawn_task(runtime_task)
        with mock.patch.object(
            LXCSpawner, "run_container_cmd", return_value=(0, "", "")
        ):
            with mock.patch.object(
                LXCSpawner, "run_container_cmd_async", return_value=(0, "", "")
            ):
                with self.assertRaises(RuntimeError):
                    asyncio.run(to_spawn)

        LXC_BACKEND.Container.assert_not_called()
        self.assertEqual(LXCSpawner.slots_cache, {"c1": True})

    def test_slots_cache_empty(self):
        """Checks if no slots could be used from cache with expected errors."""
        runtime_task = mock.MagicMock()
        runtime_task.spawner_handle = None
        self.spawner.config["spawner.lxc.slots"] = []

        to_spawn = self.spawner.spawn_task(runtime_task)
        with mock.patch.object(
            LXCSpawner, "run_container_cmd", return_value=(0, "", "")
        ):
            with mock.patch.object(
                LXCSpawner, "run_container_cmd_async", return_value=(0, "", "")
            ):
                with self.assertRaises(RuntimeError):
                    asyncio.run(to_spawn)

        LXC_BACKEND.Container.assert_not_called()
        self.assertEqual(LXCSpawner.slots_cache, {})
