import asyncio
import collections
import logging
import multiprocessing
import time

from avocado.core.exceptions import JobFailFast
from avocado.core.task.runtime import RuntimeTaskStatus
from avocado.core.teststatus import STATUSES_NOT_OK

LOG = logging.getLogger(__name__)


class TaskStateMachine:
    """Represents all phases that a task can go through its life."""

    def __init__(self, tasks, status_repo):
        self._requested = collections.deque(tasks)
        self._status_repo = status_repo
        self._triaging = []
        self._ready = []
        self._started = []
        self._monitored = []
        self._finished = []
        self._lock = asyncio.Lock()
        self._cache_lock = asyncio.Lock()
        self._task_size = len(tasks)

        self._tasks_by_id = {
            str(runtime_task.task.identifier): runtime_task.task
            for runtime_task in tasks
        }

    @property
    def requested(self):
        return self._requested

    @property
    def triaging(self):
        return self._triaging

    @property
    def ready(self):
        return self._ready

    @property
    def started(self):
        return self._started

    @property
    def monitored(self):
        return self._monitored

    @property
    def finished(self):
        return self._finished

    @property
    def lock(self):
        return self._lock

    @property
    def cache_lock(self):
        return self._cache_lock

    @property
    def task_size(self):
        return self._task_size

    @property
    async def complete(self):
        async with self._lock:
            pending = any([self._requested, self._triaging, self._ready, self._started])
        return not pending

    @property
    def tasks_by_id(self):
        return self._tasks_by_id

    async def add_new_task(self, runtime_task):
        async with self.lock:
            self._requested.appendleft(runtime_task)
            self._tasks_by_id[str(runtime_task.task.identifier)] = runtime_task.task
        return

    async def abort(self, status_reason=None):
        """Abort all non-started tasks.

        This method will move all non-started tasks to finished with a specific
        reason.

        :param status_reason: string reason. Optional.
        """
        await self.abort_queue("requested", status_reason)
        await self.abort_queue("triaging", status_reason)
        await self.abort_queue("ready", status_reason)

    async def abort_queue(self, queue_name, status_reason=None):
        """Abort all tasks inside a specific queue adding a status reason.

        :param queue_name: a string with the queue name.
        :param status_reason: string reason. Optional.
        """
        to_remove = []
        async with self._lock:
            queue = getattr(self, queue_name)
            for _ in range(len(queue)):
                if queue_name == "requested":
                    runtime_task = queue.popleft()
                else:
                    runtime_task = queue.pop(0)
                to_remove.append(runtime_task)

        if to_remove:
            if status_reason:
                LOG.debug(
                    'Aborting queue "%s" by finishing %u tasks: %s',
                    queue_name,
                    len(to_remove),
                    status_reason,
                )
            else:
                LOG.debug(
                    'Aborting queue "%s" by finishing %u tasks',
                    queue_name,
                    len(to_remove),
                )

        for task in to_remove:
            await self.finish_task(task, status_reason)

    async def finish_task(self, runtime_task, status_reason=None):
        """Include a task to the finished queue with a specific reason.

        This method is assuming that you have removed (pop) the task from the
        original queue.

        :param runtime_task: A running task object.
        :param status_reason: string reason. Optional.
        """
        async with self._lock:
            if runtime_task not in self.finished:
                if status_reason:
                    runtime_task.status = status_reason
                    LOG.debug(
                        'Task "%s" finished with status: %s',
                        runtime_task.task.identifier,
                        status_reason,
                    )
                else:
                    LOG.debug('Task "%s" finished', runtime_task.task.identifier)
                self.finished.append(runtime_task)


class Worker:
    def __init__(
        self,
        state_machine,
        spawner,
        max_triaging=None,
        max_running=None,
        task_timeout=None,
        failfast=False,
    ):
        self._state_machine = state_machine
        self._spawner = spawner
        if max_triaging is None:
            max_triaging = multiprocessing.cpu_count()
        self._max_triaging = max_triaging
        if max_running is None:
            max_running = 2 * multiprocessing.cpu_count() - 1
        self._max_running = max_running
        self._task_timeout = task_timeout
        self._failfast = failfast
        LOG.debug("%s has been initialized", self)

    def __repr__(self):
        fmt = '<Worker spawner="{}" max_triaging={} max_running={} task_timeout={}>'
        return fmt.format(
            self._spawner, self._max_triaging, self._max_running, self._task_timeout
        )

    async def _send_finished_tasks_message(self, terminate_tasks, reason):
        """Sends messages related to timeout to status repository.
        When the task is terminated, it is necessary to send a finish message to status
        repository to close logging. This method will send log message with timeout
        information and finish message with right fail reason.

        :param terminate_tasks: runtime_tasks which were terminated
        :type terminate_tasks: list
        """
        for terminated_task in terminate_tasks:
            task_id = str(terminated_task.task.identifier)
            job_id = terminated_task.task.job_id
            encoding = "utf-8"
            log_message = {
                "status": "running",
                "type": "log",
                "log": f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} | "
                f"Runner error occurred: {reason}".encode(encoding),
                "encoding": encoding,
                "time": time.monotonic(),
                "id": task_id,
                "job_id": job_id,
            }
            finish_message = {
                "status": "finished",
                "result": "interrupted",
                "fail_reason": f"Test interrupted: {reason}",
                "time": time.monotonic(),
                "id": task_id,
                "job_id": job_id,
            }
            try:
                current_status, _ = self._state_machine._status_repo._status[task_id]
            except KeyError:
                return
            if current_status != "finished":
                self._state_machine._status_repo.process_message(log_message)
                self._state_machine._status_repo.process_message(finish_message)

    async def bootstrap(self):
        """Reads from requested, moves into triaging."""
        try:
            async with self._state_machine.lock:
                if len(self._state_machine.triaging) < self._max_triaging:
                    runtime_task = self._state_machine.requested.popleft()
                    self._state_machine.triaging.append(runtime_task)
                    LOG.debug(
                        'Task "%s": requested -> triaging', runtime_task.task.identifier
                    )
                else:
                    return
        except IndexError:
            return

    async def triage(self):
        """Reads from triaging, moves into either: ready or finished."""

        try:
            async with self._state_machine.lock:
                runtime_task = self._state_machine.triaging.pop(0)
        except IndexError:
            return

        # a task waiting requirements already checked its requirements
        if runtime_task.status != RuntimeTaskStatus.WAIT_DEPENDENCIES:
            # check for requirements a task may have
            requirements_ok = await self._spawner.check_task_requirements(runtime_task)
            if requirements_ok:
                LOG.debug(
                    'Task "%s": requirements OK (will proceed to check '
                    "dependencies)",
                    runtime_task.task.identifier,
                )
            else:
                await self._state_machine.finish_task(
                    runtime_task, RuntimeTaskStatus.FAIL_TRIAGE
                )
                return

        # handle task dependencies
        if runtime_task.dependencies:
            # check of all the dependency tasks finished
            if not runtime_task.are_dependencies_finished():
                async with self._state_machine.lock:
                    self._state_machine.triaging.append(runtime_task)
                    runtime_task.status = RuntimeTaskStatus.WAIT_DEPENDENCIES
                await asyncio.sleep(0.1)
                return

            # dependencies finished, let's check if they finished
            # successfully, so we can move on with the parent task
            dependencies_ok = runtime_task.can_run()
            if not dependencies_ok:
                LOG.debug(
                    'Task "%s" has failed dependencies', runtime_task.task.identifier
                )
                runtime_task.result = "fail"
                await self._state_machine.finish_task(
                    runtime_task, RuntimeTaskStatus.FAIL_TRIAGE
                )
                return
        if runtime_task.task.category != "test":
            # save or retrieve task from cache
            if runtime_task.is_cacheable:
                async with self._state_machine.cache_lock:
                    is_task_in_cache = await self._spawner.is_requirement_in_cache(
                        runtime_task
                    )
                    if is_task_in_cache is None:
                        async with self._state_machine.lock:
                            self._state_machine.triaging.append(runtime_task)
                            runtime_task.status = RuntimeTaskStatus.WAIT
                            await asyncio.sleep(0.1)
                        return

                    if is_task_in_cache:
                        task_id = str(runtime_task.task.identifier)
                        job_id = runtime_task.task.job_id
                        encoding = "utf-8"
                        start_message = {
                            "status": "started",
                            "time": time.monotonic(),
                            "output_dir": runtime_task.task.runnable.output_dir,
                            "id": task_id,
                            "job_id": job_id,
                        }
                        log_message = {
                            "status": "running",
                            "type": "log",
                            "log": f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} | "
                            f"Dependency fulfilled from cache.".encode(encoding),
                            "encoding": encoding,
                            "time": time.monotonic(),
                            "id": task_id,
                            "job_id": job_id,
                        }
                        finish_message = {
                            "status": "finished",
                            "result": "pass",
                            "time": time.monotonic(),
                            "id": task_id,
                            "job_id": job_id,
                        }
                        self._state_machine._status_repo.process_message(start_message)
                        self._state_machine._status_repo.process_message(log_message)
                        self._state_machine._status_repo.process_message(finish_message)
                        await self._state_machine.finish_task(
                            runtime_task, RuntimeTaskStatus.IN_CACHE
                        )
                        runtime_task.result = "pass"
                        return

                    await self._spawner.save_requirement_in_cache(runtime_task)

        # the task is ready to run
        async with self._state_machine.lock:
            self._state_machine.ready.append(runtime_task)

    async def start(self):
        """Reads from ready, moves into either: started or finished."""
        try:
            async with self._state_machine.lock:
                runtime_task = self._state_machine.ready.pop(0)
        except IndexError:
            return

        # enforce a rate limit on the number of started (currently
        # running) tasks.  this is a global limit, but the spawners
        # can also be queried with regards to their capacity to handle
        # new tasks
        should_wait = False
        async with self._state_machine.lock:
            if len(self._state_machine.started) >= self._max_running:
                self._state_machine.ready.insert(0, runtime_task)
                runtime_task.status = RuntimeTaskStatus.WAIT
                should_wait = True
        if should_wait:
            await asyncio.sleep(0.1)
            return

        LOG.debug(
            'Task "%s": about to be spawned with "%s"',
            runtime_task.task.identifier,
            self._spawner,
        )
        start_ok = await self._spawner.spawn_task(runtime_task)
        if start_ok:
            LOG.debug('Task "%s": spawned successfully', runtime_task.task.identifier)
            runtime_task.status = RuntimeTaskStatus.STARTED
            if self._task_timeout is not None:
                runtime_task.execution_timeout = time.monotonic() + self._task_timeout
            async with self._state_machine.lock:
                self._state_machine.started.append(runtime_task)
        else:
            await self._state_machine.finish_task(
                runtime_task, RuntimeTaskStatus.FAIL_START
            )

    async def monitor(self):
        """Reads from started, moves into finished."""
        try:
            async with self._state_machine.lock:
                runtime_task = self._state_machine.started.pop(0)
        except IndexError:
            return

        if self._spawner.is_task_alive(runtime_task):
            async with self._state_machine.lock:
                self._state_machine._monitored.append(runtime_task)
            try:
                if runtime_task.execution_timeout is None:
                    remaining = None
                else:
                    remaining = runtime_task.execution_timeout - time.monotonic()
                await asyncio.wait_for(self._spawner.wait_task(runtime_task), remaining)
            except asyncio.TimeoutError:
                await self._terminate_task(runtime_task, RuntimeTaskStatus.TIMEOUT)
                await self._send_finished_tasks_message(
                    [runtime_task], "Timeout reached"
                )
            async with self._state_machine.lock:
                try:
                    self._state_machine.monitored.remove(runtime_task)
                except ValueError:
                    pass

        # from here, this `task` ran, so, let's check
        # the its latest data in the status repo
        latest_task_data = (
            self._state_machine._status_repo.get_latest_task_data(
                str(runtime_task.task.identifier)
            )
            or {}
        )
        # maybe, the results are not available yet
        while latest_task_data.get("result") is None:
            await asyncio.sleep(0.1)
            latest_task_data = (
                self._state_machine._status_repo.get_latest_task_data(
                    str(runtime_task.task.identifier)
                )
                or {}
            )
        if runtime_task.task.category != "test":
            async with self._state_machine.cache_lock:
                await self._spawner.update_requirement_cache(
                    runtime_task, latest_task_data["result"].upper()
                )
        runtime_task.result = latest_task_data["result"]
        result_stats = set(
            key.upper() for key in self._state_machine._status_repo.result_stats.keys()
        )
        if self._failfast and not result_stats.isdisjoint(STATUSES_NOT_OK):
            await self._state_machine.abort(RuntimeTaskStatus.FAILFAST)
            raise JobFailFast("Interrupting job (failfast).")

        await self._state_machine.finish_task(runtime_task, RuntimeTaskStatus.FINISHED)

    async def _terminate_task(self, runtime_task, task_status):
        runtime_task.status = task_status
        await self._spawner.terminate_task(runtime_task)

    async def _terminate_tasks(self, task_status):
        await self._state_machine.abort(task_status)
        terminated = []
        while True:
            async with self._state_machine.lock:
                try:
                    runtime_task = self._state_machine.monitored.pop(0)
                    await self._terminate_task(runtime_task, task_status)
                    terminated.append(runtime_task)
                except IndexError:
                    if (
                        len(self._state_machine.finished) + len(terminated)
                        == self._state_machine.task_size
                    ):
                        break
        return terminated

    async def terminate_tasks_timeout(self):
        """Terminate all running tasks with a timeout message."""
        task_status = RuntimeTaskStatus.TIMEOUT
        terminated = await self._terminate_tasks(task_status)
        await self._send_finished_tasks_message(terminated, "Timeout reached")

    async def terminate_tasks_interrupted(self):
        """Terminate all running tasks with an interrupted message."""
        task_status = RuntimeTaskStatus.INTERRUPTED
        terminated = await self._terminate_tasks(task_status)
        await self._send_finished_tasks_message(terminated, "Interrupted by user")

    async def run(self):
        """Pushes Tasks forward and makes them do something with their lives."""
        while True:
            is_complete = await self._state_machine.complete
            if is_complete:
                break
            await self.bootstrap()
            await self.triage()
            await self.start()
            await self.monitor()
