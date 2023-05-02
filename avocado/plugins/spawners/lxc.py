import asyncio
import contextlib
import logging
import os
import tempfile

try:
    import lxc

    LXC_AVAILABLE = True
except ImportError:
    lxc = None
    LXC_AVAILABLE = False

from avocado.core.plugin_interfaces import Init, Spawner
from avocado.core.settings import settings
from avocado.core.spawners.common import SpawnerMixin, SpawnMethod

LOG = logging.getLogger(__name__)


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
        os.remove(self.path)


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
            return await fn(self, runtime_task)

    return wrapper


class LXCSpawner(Spawner, SpawnerMixin):

    description = "LXC (container) based spawner"
    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE]
    slots_cache = {}

    @staticmethod
    def run_container_cmd(container, command):
        with LXCStreamsFile() as tmp_out, LXCStreamsFile() as tmp_err:
            exitcode = container.attach_wait(
                lxc.attach_run_command, command, stdout=tmp_out, stderr=tmp_err
            )
            return exitcode, tmp_out.read(), tmp_err.read()

    @staticmethod
    async def run_container_cmd_async(container, command):
        with LXCStreamsFile() as tmp_out, LXCStreamsFile() as tmp_err:
            pid = container.attach(
                lxc.attach_run_command, command, stdout=tmp_out, stderr=tmp_err
            )
            loop = asyncio.get_event_loop()
            _, exitcode = await loop.run_in_executor(
                None, os.waitpid, pid, os.WUNTRACED
            )
            return exitcode, tmp_out.read(), tmp_err.read()

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

        if runtime_task.spawner_handle is not None:
            slot = runtime_task.spawner_handle
        else:
            slots = LXCSpawner.slots_cache
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
            LXCSpawner.slots_cache[slot] = False

    @staticmethod
    def is_task_alive(runtime_task):
        if runtime_task.spawner_handle is None:
            return False

        container = lxc.Container(runtime_task.spawner_handle)
        if not container.defined:
            LOG.debug(f"Container {runtime_task.spawner_handle} is not defined")
            return False
        if not container.running:
            LOG.debug(
                f"Container {runtime_task.spawner_handle} state is "
                f"{container.state} instead of RUNNING"
            )
            return False

        status, _, _ = LXCSpawner.run_container_cmd(
            container, ["pgrep", "-r", "R,S", "-f", "task-run"]
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
            raise LXCSpawnerException(msg)
        # using the "python" symlink will result in the container default python version
        entry_point_args = ["python3", "-m", full_module_name, "task-run"]
        entry_point_args.extend(task.get_command_args())

        dist = self.config.get("spawner.lxc.dist")
        release = self.config.get("spawner.lxc.release")
        arch = self.config.get("spawner.lxc.arch")
        create_hook = self.config.get("spawner.lxc.create_hook")

        if not LXC_AVAILABLE:
            msg = "LXC python bindings not available on the system"
            runtime_task.status = msg
            return False

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
                exitcode, output, err = await LXCSpawner.run_container_cmd_async(
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

        exitcode, output, err = await LXCSpawner.run_container_cmd_async(
            container, entry_point_args
        )
        LOG.debug(f"Command exited with code {exitcode}")
        if exitcode != 0:
            LOG.error(f"Error '{err}' on {container_id} with output:\n{output}")
            return False

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

    async def terminate_task(self, runtime_task):
        container = lxc.Container(runtime_task.spawner_handle)

        # Stop the container
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
