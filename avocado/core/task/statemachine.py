import asyncio
import multiprocessing
import time


class TaskStateMachine:
    """Represents all phases that a task can go through its life."""
    def __init__(self, tasks):
        self._requested = tasks
        self._triaging = []
        self._ready = []
        self._started = []
        self._finished = []
        self._lock = asyncio.Lock()

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
    def finished(self):
        return self._finished

    @property
    def lock(self):
        return self._lock

    @property
    async def complete(self):
        async with self._lock:
            pending = any([self._requested, self._triaging,
                           self._ready, self._started])
        return not pending


class Worker:

    def __init__(self, state_machine, spawner,
                 max_triaging=None, max_running=None, task_timeout=None):
        self._state_machine = state_machine
        self._spawner = spawner
        if max_triaging is None:
            max_triaging = multiprocessing.cpu_count()
        self._max_triaging = max_triaging
        if max_running is None:
            max_running = 2 * multiprocessing.cpu_count() - 1
        self._max_running = max_running
        self._task_timeout = task_timeout

    async def bootstrap(self):
        """Reads from requested, moves into triaging."""
        try:
            async with self._state_machine.lock:
                if len(self._state_machine.triaging) < self._max_triaging:
                    runtime_task = self._state_machine.requested.pop(0)
                    self._state_machine.triaging.append(runtime_task)
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

        requirements_ok = await self._spawner.check_task_requirements(runtime_task)
        if requirements_ok:
            async with self._state_machine.lock:
                self._state_machine.ready.append(runtime_task)
        else:
            async with self._state_machine.lock:
                self._state_machine.finished.append(runtime_task)
                runtime_task.status = 'FAILED ON TRIAGE'

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
                runtime_task.status = 'WAITING'
                should_wait = True
        if should_wait:
            await asyncio.sleep(0.1)
            return

        start_ok = await self._spawner.spawn_task(runtime_task)
        if start_ok:
            runtime_task.status = None
            if self._task_timeout is not None:
                runtime_task.execution_timeout = time.monotonic() + self._task_timeout
            async with self._state_machine.lock:
                self._state_machine.started.append(runtime_task)
        else:
            async with self._state_machine.lock:
                self._state_machine.finished.append(runtime_task)

    async def monitor(self):
        """Reads from started, moves into finished."""
        try:
            async with self._state_machine.lock:
                runtime_task = self._state_machine.started.pop(0)
        except IndexError:
            return

        if self._spawner.is_task_alive(runtime_task):
            try:
                if runtime_task.execution_timeout is None:
                    remaining = None
                else:
                    remaining = runtime_task.timeout - time.monotonic()
                await asyncio.wait_for(self._spawner.wait_task(runtime_task),
                                       remaining)
                runtime_task.status = 'FINISHED'
            except asyncio.TimeoutError:
                runtime_task.status = 'FINISHED W/ TIMEOUT'

        async with self._state_machine.lock:
            self._state_machine.finished.append(runtime_task)

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
