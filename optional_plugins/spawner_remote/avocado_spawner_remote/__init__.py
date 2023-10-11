import asyncio
import contextlib
import json
import logging
import os
import shlex

from aexpect import exceptions, remote

from avocado.core.plugin_interfaces import Init, Spawner
from avocado.core.settings import settings
from avocado.core.spawners.common import SpawnerMixin, SpawnMethod

LOG = logging.getLogger("avocado.job." + __name__)


class RemoteSpawnerException(Exception):
    """Errors more closely related to the spawner functionality"""


class RemoteSpawnerInit(Init):

    description = "Remote (host) based spawner initialization"

    def initialize(self):
        section = "spawner.remote"

        help_msg = "List of already available remote host slots to spawn in"
        settings.register_option(
            section=section, key="slots", help_msg=help_msg, key_type=list, default=[]
        )

        help_msg = "Remote host setup hook command to customize optional new hosts"
        settings.register_option(
            section=section, key="setup_hook", help_msg=help_msg, default=""
        )

        help_msg = "Test timeout enforced for sessions (just for this spawner)"
        settings.register_option(
            section=section, key="test_timeout", help_msg=help_msg, default=14400
        )


def with_slot_reservation(fn):
    """
    Decorator for slot cache context manager.

    :param fn: function to run with slot reservation
    :type fn: function
    :returns: same function with the slot now reserved
    :rtype: function

    The main reason for the decorator is to not have to indent the entire
    task running function in order to safely release the slot upon any error.
    """

    async def wrapper(self, runtime_task):
        with RemoteSpawner.reserve_slot(self, runtime_task) as slot:
            runtime_task.spawner_handle = slot
            return await fn(self, runtime_task)

    return wrapper


class RemoteSpawner(Spawner, SpawnerMixin):

    description = "Remote (host) based spawner"
    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE]
    slots_cache = {}

    @staticmethod
    async def run_remote_cmd_async(session, command, timeout):
        loop = asyncio.get_event_loop()
        try:
            status, output = await loop.run_in_executor(
                None, session.cmd_status_output, command, timeout
            )
        except exceptions.ShellTimeoutError:
            status, output = 2, f"Remote command timeout of {timeout} reached"
        except exceptions.ShellProcessTerminatedError:
            status, output = 2, "Remote command terminated prematurely"
        return status, output

    @contextlib.contextmanager
    def reserve_slot(self, runtime_task):
        """
        Reserve a free or custom remote host slot for the runtime task.

        :param runtime_task: runtime task to reserve the slot for
        :type runtime_task: :py:class:`avocado.core.task.runtime.RuntimeTask`
        :yields: a free slot to use if such was found
        :raises: :py:class:`RuntimeError` if no free slot could be found

        This will either use a runtime cache to find a free remote host slot to
        run the task in or use a custom hostname/slot ID to allow for custom
        schedulers to make their own decisions on which hosts to run and when.
        """
        if len(RemoteSpawner.slots_cache) == 0:
            # TODO: consider whether to provide persistence across runs via external storage
            for session_slot in self.config.get("spawner.remote.slots"):
                if not session_slot:
                    continue
                with open(session_slot, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                session = remote.remote_login(**session_data)
                RemoteSpawner.slots_cache[session] = False

        if runtime_task.spawner_handle is not None:
            slot = runtime_task.spawner_handle
        else:
            slots = RemoteSpawner.slots_cache
            for key, value in slots.items():
                if not value:
                    slot = key
                    slots[key] = True
                    break
            else:
                raise RuntimeError(
                    "No free slot available for the task, are "
                    "you running with more processes than slots?"
                )

        try:
            yield slot
        finally:
            RemoteSpawner.slots_cache[slot] = False

    @staticmethod
    def is_task_alive(runtime_task):
        if runtime_task.spawner_handle is None:
            return False
        # NOTE: since this is called at the end of each test, it is reasonable
        # to reuse the same session with a new command
        session = runtime_task.spawner_handle
        status, _ = session.cmd_status_output(
            f"pgrep -r R,S -f {runtime_task.task.identifier}"
        )
        return status == 0

    @with_slot_reservation
    async def spawn_task(self, runtime_task):
        self.create_task_output_dir(runtime_task)
        task = runtime_task.task
        full_module_name = (
            runtime_task.task.runnable.pick_runner_module_from_entry_point_kind(
                runtime_task.task.runnable.kind
            )
        )
        if full_module_name is None:
            msg = f"Could not determine Python module name for runnable with kind {runtime_task.task.runnable.kind}"
            raise RemoteSpawnerException(msg)
        # using the "python" symlink will result in the container default python version
        entry_point_args = ["python3", "-m", full_module_name, "task-run"]
        entry_point_args.extend(task.get_command_args())

        session = runtime_task.spawner_handle
        LOG.info(f"Hostname: {session.host} Port: {session.port}")

        setup_hook = self.config.get("spawner.remote.setup_hook")
        # Customize and deploy test data to the container
        if setup_hook:
            status, output = await RemoteSpawner.run_remote_cmd_async(
                session, setup_hook
            )
            LOG.debug(f"Customization command exited with code {status}")
            if status != 0:
                LOG.error(
                    f"Error exit code {status} on {session.host}:{session.port} "
                    f"from setup hook with output:\n{output}"
                )
                return False

        cmd = shlex.join(entry_point_args) + " > /dev/null"
        timeout = self.config.get("spawner.remote.test_timeout")
        status, output = await RemoteSpawner.run_remote_cmd_async(session, cmd, timeout)
        LOG.debug(f"Command exited with code {status}")
        if status != 0:
            LOG.error(
                f"Error exit code {status} on {session.host}:{session.port} "
                f"with output:\n{output}"
            )
            return False

        return True

    def create_task_output_dir(self, runtime_task):
        output_dir_path = self.task_output_dir(runtime_task)
        output_lxc_path = "/tmp/.avocado_task_output_dir"

        os.makedirs(output_dir_path, exist_ok=True)
        runtime_task.task.setup_output_dir(output_lxc_path)

    async def wait_task(self, runtime_task):
        while True:
            if not RemoteSpawner.is_task_alive(runtime_task):
                return
            await asyncio.sleep(0.1)

    async def terminate_task(self, runtime_task):
        session = runtime_task.spawner_handle
        session.sendcontrol("c")
        try:
            session.read_up_to_prompt()
            return True
        except exceptions.ExpectTimeoutError:
            LOG.error("Failed to terminate task on {session.host}")
            return False

    @staticmethod
    async def check_task_requirements(runtime_task):
        """Check the runtime task requirements needed to be able to run"""
        return True

    @staticmethod
    async def is_requirement_in_cache(runtime_task):
        return False

    @staticmethod
    async def save_requirement_in_cache(runtime_task):
        pass

    @staticmethod
    async def update_requirement_cache(runtime_task, result):
        pass
