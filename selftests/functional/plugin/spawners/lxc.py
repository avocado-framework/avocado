import asyncio
import os
import signal
from unittest import mock

from avocado import Test
from avocado.core.job import Job
from avocado.plugins.spawners import lxc
from avocado.plugins.spawners.lxc import LXCSpawner, LXCStreamsFile
from selftests.utils import BASEDIR

LXC_BACKEND = mock.MagicMock()


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
        self.spawner.create_task_output_dir = mock.Mock()

    def tearDown(self):
        LXC_BACKEND.reset_mock()

    def test_streams_file_cleanup(self):
        """Checks that temporary stream descriptors and paths are released."""
        with LXCStreamsFile() as stream:
            fd = stream.fd
            path = stream.path
            os.fstat(fd)

        with self.assertRaises(OSError):
            os.fstat(fd)
        self.assertFalse(os.path.exists(path))

    def test_async_command_discards_streams(self):
        """Checks that detached command output is safely discarded."""
        container = mock.MagicMock()
        container.attach.return_value = 123

        result = asyncio.run(LXCSpawner.run_container_cmd_async(container, ["cmd"]))

        self.assertEqual(result, (123, "", ""))
        stream = container.attach.call_args.kwargs["stdout"]
        self.assertIs(stream, container.attach.call_args.kwargs["stderr"])
        self.assertTrue(stream.closed)

    def test_terminate_task_tracked_pid(self):
        """Checks that termination targets the attached task PID."""
        runtime_task = mock.MagicMock(spawner_handle="c1", lxc_task_pid=123)
        LXCSpawner.slots_cache = {"c1": True}

        with (
            mock.patch("avocado.plugins.spawners.lxc.os.kill") as kill,
            mock.patch(
                "avocado.plugins.spawners.lxc.os.waitpid", return_value=(123, 0)
            ),
        ):
            self.assertTrue(asyncio.run(self.spawner.terminate_task(runtime_task)))

        kill.assert_called_once_with(123, signal.SIGTERM)
        LXC_BACKEND.Container.assert_not_called()
        self.assertFalse(LXCSpawner.slots_cache["c1"])

    def test_terminate_task_escalates_to_sigkill(self):
        """Checks that an unresponsive task is forcibly terminated."""
        runtime_task = mock.MagicMock(spawner_handle="c1", lxc_task_pid=123)
        LXCSpawner.slots_cache = {"c1": True}

        with (
            mock.patch("avocado.plugins.spawners.lxc.os.kill") as kill,
            mock.patch(
                "avocado.plugins.spawners.lxc.os.waitpid",
                side_effect=[(0, 0), (123, 0)],
            ),
            mock.patch("avocado.plugins.spawners.lxc.TERMINATE_GRACE_PERIOD", 0),
        ):
            self.assertTrue(asyncio.run(self.spawner.terminate_task(runtime_task)))

        self.assertEqual(
            kill.call_args_list,
            [mock.call(123, signal.SIGTERM), mock.call(123, signal.SIGKILL)],
        )
        LXC_BACKEND.Container.assert_not_called()
        self.assertFalse(LXCSpawner.slots_cache["c1"])

    def test_terminate_task_falls_back_to_container(self):
        """Checks that signaling errors fall back to container shutdown."""
        runtime_task = mock.MagicMock(spawner_handle="c1", lxc_task_pid=123)
        LXCSpawner.slots_cache = {"c1": True}
        container = LXC_BACKEND.Container.return_value
        container.shutdown.return_value = True

        with (
            mock.patch(
                "avocado.plugins.spawners.lxc.os.kill",
                side_effect=PermissionError("denied"),
            ),
            mock.patch("avocado.plugins.spawners.lxc.os.waitpid", return_value=(0, 0)),
        ):
            self.assertTrue(asyncio.run(self.spawner.terminate_task(runtime_task)))

        LXC_BACKEND.Container.assert_called_once_with("c1")
        container.shutdown.assert_called_once_with(30)
        self.assertFalse(LXCSpawner.slots_cache["c1"])

    def test_slots_cache_custom(self):
        """Checks if custom (scheduler predefined) slots could be used from cache."""
        runtime_task = mock.MagicMock()
        runtime_task.spawner_handle = "c100"

        to_spawn = self.spawner.spawn_task(runtime_task)
        with mock.patch.object(
            LXCSpawner,
            "run_container_cmd",
            # status 1 means no previous task was detected
            return_value=(1, "", ""),
        ):
            with mock.patch.object(
                LXCSpawner,
                "run_container_cmd_async",
                # pid 123 (rather than <=0) means successful LXC attachment
                return_value=(123, "", ""),
            ):
                asyncio.run(to_spawn)

        LXC_BACKEND.Container.assert_called_with("c100")
        self.assertEqual(
            LXCSpawner.slots_cache,
            {"c1": False, "c2": False, "c3": False, "c100": True},
        )

    def test_slots_cache_free(self):
        """Checks if free slots could be used from cache."""
        runtime_task = mock.MagicMock()
        runtime_task.spawner_handle = None

        to_spawn = self.spawner.spawn_task(runtime_task)
        with mock.patch.object(
            LXCSpawner,
            "run_container_cmd",
            # status 1 means no previous task was detected
            return_value=(1, "", ""),
        ):
            with mock.patch.object(
                LXCSpawner,
                "run_container_cmd_async",
                # pid 123 (rather than <=0) means successful LXC attachment
                return_value=(123, "", ""),
            ):
                asyncio.run(to_spawn)

        LXC_BACKEND.Container.assert_called_with("c1")
        self.assertEqual(LXCSpawner.slots_cache, {"c1": True, "c2": False, "c3": False})

    def test_slots_cache_free_next(self):
        """Checks if free slots could be used from cache with some slots occupied."""
        runtime_task = mock.MagicMock()
        runtime_task.spawner_handle = None
        LXCSpawner.slots_cache = {"c1": True, "c2": False}

        to_spawn = self.spawner.spawn_task(runtime_task)
        with mock.patch.object(
            LXCSpawner,
            "run_container_cmd",
            # status 1 means no previous task was detected
            return_value=(1, "", ""),
        ):
            with mock.patch.object(
                LXCSpawner,
                "run_container_cmd_async",
                # pid 123 (rather than <=0) means successful LXC attachment
                return_value=(123, "", ""),
            ):
                asyncio.run(to_spawn)

        LXC_BACKEND.Container.assert_called_with("c2")
        self.assertEqual(LXCSpawner.slots_cache, {"c1": True, "c2": True})

    def test_slot_released_when_task_finishes(self):
        """Checks if occupied slots are released when a task finishes."""
        runtime_task = mock.MagicMock()
        runtime_task.spawner_handle = None

        to_spawn = self.spawner.spawn_task(runtime_task)
        with mock.patch.object(
            # status 1 means no previous task was detected
            LXCSpawner,
            "run_container_cmd",
            return_value=(1, "", ""),
        ):
            with mock.patch.object(
                LXCSpawner,
                "run_container_cmd_async",
                # pid 123 (rather than <=0) means successful LXC attachment
                return_value=(123, "", ""),
            ):
                asyncio.run(to_spawn)

        with mock.patch("avocado.plugins.spawners.lxc.os.waitpid") as waitpid:
            waitpid.side_effect = [(0, 0), (123, 0)]
            self.assertTrue(LXCSpawner.is_task_alive(runtime_task))
            self.assertFalse(LXCSpawner.is_task_alive(runtime_task))

        self.assertEqual(waitpid.call_args_list, [mock.call(123, os.WNOHANG)] * 2)
        self.assertFalse(LXCSpawner.slots_cache["c1"])

    def test_slots_cache_full(self):
        """Checks if free slots could be used from cache with some slots occupied."""
        runtime_task = mock.MagicMock()
        runtime_task.spawner_handle = None
        LXCSpawner.slots_cache = {"c1": True}

        to_spawn = self.spawner.spawn_task(runtime_task)
        with mock.patch.object(
            LXCSpawner,
            "run_container_cmd",
            # status 1 means no previous task was detected
            return_value=(1, "", ""),
        ):
            with mock.patch.object(
                LXCSpawner,
                "run_container_cmd_async",
                # pid 123 (rather than <=0) means successful LXC attachment
                return_value=(123, "", ""),
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
            LXCSpawner,
            "run_container_cmd",
            # status 1 means no previous task was detected
            return_value=(1, "", ""),
        ):
            with mock.patch.object(
                LXCSpawner,
                "run_container_cmd_async",
                # pid 123 (rather than <=0) means successful LXC attachment
                return_value=(123, "", ""),
            ):
                with self.assertRaises(RuntimeError):
                    asyncio.run(to_spawn)

        LXC_BACKEND.Container.assert_not_called()
        self.assertEqual(LXCSpawner.slots_cache, {})
