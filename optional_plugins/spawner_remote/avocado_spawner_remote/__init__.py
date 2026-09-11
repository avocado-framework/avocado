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
REMOTE_PID_MARKER = "__AVOCADO_REMOTE_PID__="
TERMINATE_GRACE_PERIOD = 30
TERMINATE_FORCE_PERIOD = 10
TERMINATE_POLL_INTERVAL = 0.1


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

        help_msg = "Test timeout enforced for remote host setup hook"
        settings.register_option(
            section=section,
            key="setup_timeout",
            help_msg=help_msg,
            key_type=int,
            default=3600,
        )

        help_msg = "Test timeout enforced for sessions (just for this spawner)"
        settings.register_option(
            section=section,
            key="test_timeout",
            help_msg=help_msg,
            key_type=int,
            default=14400,
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
            spawned = await fn(self, runtime_task)
            if not spawned:
                RemoteSpawner.release_slot(slot)
            return spawned

    return wrapper


class RemoteSpawner(Spawner, SpawnerMixin):

    description = "Remote (host) based spawner"
    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE]
    slots_cache = {}

    def is_operational(self):
        return True

    @staticmethod
    def run_remote_cmd(session, command, timeout):
        try:
            status, output = session.cmd_status_output(command, timeout, safe=True)
        except exceptions.ShellTimeoutError:
            status, output = 2, f"Remote command timeout of {timeout} reached"
        except exceptions.ShellProcessTerminatedError:
            status, output = 2, "Remote command terminated prematurely"
        except exceptions.ShellStatusError:
            status, output = 3, "Remote command could not retrieve status"
        return status, output

    @staticmethod
    def release_slot(slot):
        """Release an remote slot after spawning failed or its task exited."""
        RemoteSpawner.slots_cache[slot] = False

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

        slots = RemoteSpawner.slots_cache
        if runtime_task.spawner_handle is not None:
            slot = runtime_task.spawner_handle
            if slots.get(slot, False):
                raise RuntimeError(f"Remote slot {slot} is already reserved")
            slots[slot] = True
        else:
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
        except BaseException:
            RemoteSpawner.release_slot(slot)
            raise

    @staticmethod
    def is_task_alive(runtime_task):
        if runtime_task.spawner_handle is None:
            return False

        session = runtime_task.spawner_handle
        pid = getattr(runtime_task, "remote_task_pid", None)
        if pid is None:
            return False

        status, output = RemoteSpawner.run_remote_cmd(
            session, f"ps -o stat= -p {pid}", 10
        )
        if status == 1:
            RemoteSpawner.release_slot(session)
            return False
        if status != 0:
            LOG.error(
                "Could not check whether remote task PID %s is alive: %s",
                pid,
                output,
            )
            return True
        process_state = output.strip()
        if not process_state:
            LOG.error("Remote task PID %s returned an empty process state", pid)
            return True

        if process_state.startswith("Z"):
            RemoteSpawner.release_slot(session)
            return False
        return True

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

        status, output = RemoteSpawner.run_remote_cmd(
            session,
            "pgrep -f 'task-run'",
            10,
        )
        if status == 0:
            raise RuntimeError(
                f"A previous task is still alive but only one task "
                f"can run in a remote host ({session.host}) at a time"
            )
        elif status != 1:
            logging.warning(
                f"Could not check for previous remote task in {session.host}"
            )

        setup_hook = self.config.get("spawner.remote.setup_hook")
        # Customize and deploy test data to the container
        if setup_hook:
            setup_timeout = self.config.get("spawner.remote.setup_timeout")
            status, output = RemoteSpawner.run_remote_cmd(
                session, setup_hook, setup_timeout
            )
            LOG.debug(f"Customization command exited with code {status}")
            if status != 0:
                LOG.error(
                    f"Error exit code {status} on {session.host}:{session.port} "
                    f"from setup hook with output:\n{output}"
                )
                return False

        cmd = (
            shlex.join(entry_point_args)
            + f" > /dev/null 2>&1 & printf '{REMOTE_PID_MARKER}%s\\n' \"$!\""
        )
        status, output = RemoteSpawner.run_remote_cmd(session, cmd, 10)
        pid = None
        for line in output.splitlines():
            line = line.strip()
            if line.startswith(REMOTE_PID_MARKER):
                value = line.removeprefix(REMOTE_PID_MARKER)
                if value.isdecimal():
                    pid = int(value)
        if status != 0 or not pid:
            LOG.error(
                f"Error spawning task (PID {pid}): {status} status "
                f"on {session.host}:{session.port} with output:\n{output}"
            )
            return False
        else:
            LOG.debug(f"Task spawned remotely with PID {pid}")

        runtime_task.remote_task_pid = pid

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

    @staticmethod
    async def _wait_task_exit(runtime_task, timeout):
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while RemoteSpawner.is_task_alive(runtime_task):
            remaining = deadline - loop.time()
            if remaining <= 0:
                return False
            await asyncio.sleep(min(TERMINATE_POLL_INTERVAL, remaining))
        return True

    async def terminate_task(self, runtime_task):
        session = runtime_task.spawner_handle
        pid = getattr(runtime_task, "remote_task_pid", None)
        if session is None or pid is None:
            LOG.error("Remote task has no session or tracked PID to terminate")
            return False

        status, output = RemoteSpawner.run_remote_cmd(session, f"kill -TERM {pid}", 10)
        if status not in (0, 1):
            LOG.warning("Could not send SIGTERM to remote task PID %s: %s", pid, output)
        if await RemoteSpawner._wait_task_exit(runtime_task, TERMINATE_GRACE_PERIOD):
            return True

        status, output = RemoteSpawner.run_remote_cmd(session, f"kill -KILL {pid}", 10)
        if status not in (0, 1):
            LOG.error("Could not send SIGKILL to remote task PID %s: %s", pid, output)
        if not await RemoteSpawner._wait_task_exit(
            runtime_task, TERMINATE_FORCE_PERIOD
        ):
            LOG.error("Remote task PID %s did not terminate", pid)
            return False

        RemoteSpawner.release_slot(session)
        return True

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
