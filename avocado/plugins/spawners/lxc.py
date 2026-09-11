import asyncio
import contextlib
import logging
import os
import signal
import tempfile

try:
    import lxc

    LXC_AVAILABLE = True
except ImportError:
    lxc = None
    LXC_AVAILABLE = False

from avocado.core.plugin_interfaces import Init, Spawner
from avocado.core.settings import settings
from avocado.core.spawners.common import SpawnCapabilities, SpawnerMixin, SpawnMethod

LOG = logging.getLogger(__name__)
TERMINATE_GRACE_PERIOD = 30
TERMINATE_FORCE_PERIOD = 10
TERMINATE_POLL_INTERVAL = 0.1


class LXCSpawnerException(Exception):
    """Errors more closely related to the spawner functionality"""


class LXCStreamsFile:
    def __init__(self):
        self.fd = None
        self.path = None

    def fileno(self):
        return self.fd

    def read(self):
        with open(self.path, "r", encoding="utf-8") as fp:
            return fp.read()

    def __enter__(self):
        self.fd, self.path = tempfile.mkstemp()
        return self

    def __exit__(self, *args):
        fd, self.fd = self.fd, None
        path, self.path = self.path, None
        try:
            if fd is not None:
                os.close(fd)
        finally:
            if path is not None:
                os.remove(path)


class LXCSpawnerInit(Init):

    description = "LXC (container) based spawner initialization"

    def initialize(self):
        section = "spawner.lxc"

        help_msg = "List of already available container slots to spawn in"
        settings.register_option(
            section=section, key="slots", help_msg=help_msg, key_type=list, default=[]
        )

        help_msg = "Distribution for the LXC container"
        settings.register_option(
            section=section, key="dist", help_msg=help_msg, default="fedora"
        )

        help_msg = "Release of the LXC container (depends on the choice of distro)"
        settings.register_option(
            section=section, key="release", help_msg=help_msg, default="32"
        )

        help_msg = "Architecture of the LXC container"
        settings.register_option(
            section=section, key="arch", help_msg=help_msg, default="i386"
        )

        help_msg = (
            "Container creation hook command to customize optional new containers"
        )
        settings.register_option(
            section=section, key="create_hook", help_msg=help_msg, default=""
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
        with LXCSpawner.reserve_slot(self, runtime_task) as slot:
            runtime_task.spawner_handle = slot
            spawned = await fn(self, runtime_task)
            if not spawned:
                LXCSpawner.release_slot(slot)
            return spawned

    return wrapper


class LXCSpawner(Spawner, SpawnerMixin):

    description = "LXC (container) based spawner"
    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE]
    CAPABILITIES = [
        SpawnCapabilities.AVOCADO_DEPLOYMENT,
        SpawnCapabilities.ENVIRONMENT_PRESERVATION,
    ]
    slots_cache = {}

    def is_operational(self):
        if not LXC_AVAILABLE:
            LOG.error("LXC python bindings not available on the system")
            return False
        return True

    @staticmethod
    def run_container_cmd(container, command):
        with LXCStreamsFile() as tmp_out, LXCStreamsFile() as tmp_err:
            exitcode = container.attach_wait(
                lxc.attach_run_command, command, stdout=tmp_out, stderr=tmp_err
            )
            LOG.debug(
                f"Container sync command '{command}' returned exit code {exitcode}"
            )
            return exitcode, tmp_out.read(), tmp_err.read()

    @staticmethod
    async def run_container_cmd_async(container, command):
        with open(os.devnull, "wb") as devnull:
            pid = container.attach(
                lxc.attach_run_command, command, stdout=devnull, stderr=devnull
            )
            LOG.debug(f"Container async command '{command}' returned PID {pid}")
            return pid, "", ""

    @staticmethod
    def release_slot(slot):
        """Release an LXC slot after spawning failed or its task exited."""
        LXCSpawner.slots_cache[slot] = False

    @contextlib.contextmanager
    def reserve_slot(self, runtime_task):
        """
        Reserve a free or custom container slot for the runtime task.

        :param runtime_task: runtime task to reserve the slot for
        :type runtime_task: :py:class:`avocado.core.task.runtime.RuntimeTask`
        :yields: a free slot to use if such was found
        :raises: :py:class:`RuntimeError` if no free slot could be found

        This will either use a runtime cache to find a free container slot to
        run the task in or use a custom container/slot ID to allow for custom
        schedulers to make their own decisions on which containers to run when.
        """
        if len(LXCSpawner.slots_cache) == 0:
            # TODO: consider whether to provide persistence across runs via external storage
            LXCSpawner.slots_cache = {
                k: False for k in self.config.get("spawner.lxc.slots") if k
            }
            # TODO: spawner can look for free containers directly and populate these slots
            # for c in lxcontainer.list_containers(as_object=True): ...

        slots = LXCSpawner.slots_cache
        if runtime_task.spawner_handle is not None:
            slot = runtime_task.spawner_handle
            if slots.get(slot, False):
                raise RuntimeError(f"LXC slot {slot} is already reserved")
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
            LXCSpawner.release_slot(slot)
            raise

    @staticmethod
    def is_task_alive(runtime_task):
        if runtime_task.spawner_handle is None:
            return False

        pid = getattr(runtime_task, "lxc_task_pid", None)
        if pid is None:
            return False

        try:
            finished_pid, _ = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            finished_pid = pid
        except OSError as error:
            LOG.error(
                "Could not check whether LXC task PID %s is alive: %s", pid, error
            )
            return True

        if finished_pid == 0:
            return True
        LXCSpawner.release_slot(runtime_task.spawner_handle)
        return False

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
            raise LXCSpawnerException(msg)
        # using the "python" symlink will result in the container default python version
        entry_point_args = ["python3", "-m", full_module_name, "task-run"]
        entry_point_args.extend(task.get_command_args())

        dist = self.config.get("spawner.lxc.dist")
        release = self.config.get("spawner.lxc.release")
        arch = self.config.get("spawner.lxc.arch")
        create_hook = self.config.get("spawner.lxc.create_hook")

        container_id = runtime_task.spawner_handle
        container = lxc.Container(container_id)
        if not container.defined:
            # Create the container rootfs
            if not container.create(
                "download",
                lxc.LXC_CREATE_QUIET,
                {"dist": dist, "release": release, "arch": arch},
            ):
                LOG.error("Failed to create the container rootfs")
                return False

            # Customize and deploy test data to the container
            if create_hook:
                customization_args = create_hook.split()
                exitcode, output, err = LXCSpawner.run_container_cmd(
                    container, customization_args
                )
                LOG.debug(f"Customization command exited with code {exitcode}")
                if exitcode != 0:
                    LOG.error(f"Error '{err}' on {container_id} with output:\n{output}")
                    return False

        # Start the container
        if not container.running:
            if not container.start():
                LOG.error("Failed to start the container")
                return False

        # Wait for connectivity
        # TODO: The current networking is not good enough to connect to the status server
        if not container.get_ips(timeout=30):
            LOG.error("Failed to connect to the container")
            return False

        # Query some information
        LOG.info(f"Container state: {container.state}")
        LOG.info(f"Container ID: {container_id} PID: {container.init_pid}")

        exitcode, _, _ = LXCSpawner.run_container_cmd(
            container, ["pgrep", "-f", "task-run"]
        )
        if exitcode == 0:
            raise RuntimeError(
                f"A previous task is still alive but only one task "
                f"can run in an LXC container {container.name} at a time"
            )
        elif exitcode != 1:
            logging.warning(
                f"Could not check for previous LXC task in {container.name}"
            )

        pid, output, err = await LXCSpawner.run_container_cmd_async(
            container, entry_point_args
        )
        if pid <= 0:
            LOG.error(
                f"Error spawning task (PID {pid}): '{err}' error "
                f"on {container_id} with output:\n{output}"
            )
            return False
        else:
            LOG.debug(f"Task spawned in container with PID {pid}")

        runtime_task.lxc_task_pid = pid

        return True

    def create_task_output_dir(self, runtime_task):
        output_dir_path = self.task_output_dir(runtime_task)
        output_lxc_path = "/tmp/.avocado_task_output_dir"

        os.makedirs(output_dir_path, exist_ok=True)
        runtime_task.task.setup_output_dir(output_lxc_path)

    async def wait_task(self, runtime_task):
        while True:
            if not LXCSpawner.is_task_alive(runtime_task):
                return
            await asyncio.sleep(0.1)

    @staticmethod
    async def _wait_task_exit(runtime_task, timeout):
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while LXCSpawner.is_task_alive(runtime_task):
            remaining = deadline - loop.time()
            if remaining <= 0:
                return False
            await asyncio.sleep(min(TERMINATE_POLL_INTERVAL, remaining))
        return True

    async def terminate_task(self, runtime_task):
        pid = getattr(runtime_task, "lxc_task_pid", None)
        if pid is not None:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except OSError as error:
                LOG.warning("Could not send SIGTERM to LXC task PID %s: %s", pid, error)
            else:
                if await LXCSpawner._wait_task_exit(
                    runtime_task, TERMINATE_GRACE_PERIOD
                ):
                    return True

                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except OSError as error:
                    LOG.error(
                        "Could not send SIGKILL to LXC task PID %s: %s", pid, error
                    )
                else:
                    if await LXCSpawner._wait_task_exit(
                        runtime_task, TERMINATE_FORCE_PERIOD
                    ):
                        return True

            if await LXCSpawner._wait_task_exit(runtime_task, 0):
                return True

        LOG.warning("Falling back to shutting down the LXC container")
        container = lxc.Container(runtime_task.spawner_handle)

        if not container.shutdown(30):
            LOG.warning("Failed to cleanly shutdown the container, forcing.")
            if not container.stop():
                LOG.error("Failed to kill the container")
                return False

        # TODO: we can provide extra options to not just stop but destroy the container
        # Destroy the container
        # if not container.destroy():
        #     LOG.error("Failed to destroy the container.")
        #     return False
        LXCSpawner.release_slot(runtime_task.spawner_handle)
        return True

    @staticmethod
    async def check_task_requirements(runtime_task):
        """Check the runtime task requirements needed to be able to run"""
        # right now, limit the check to the LXC availability
        return LXC_AVAILABLE

    @staticmethod
    async def is_requirement_in_cache(runtime_task):
        return False

    @staticmethod
    async def save_requirement_in_cache(runtime_task):
        pass

    @staticmethod
    async def update_requirement_cache(runtime_task, result):
        pass
