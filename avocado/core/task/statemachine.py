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

    def __init__(self, task_state_machine, spawner,
                 max_triaging=None, max_running=None, task_timeout=None):
        self._tsm = task_state_machine
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
            async with self._tsm.lock:
                if len(self._tsm.triaging) < self._max_triaging:
                    task_info = self._tsm.requested.pop()
                    self._tsm.triaging.append(task_info)
                else:
                    return
        except IndexError:
            return

    async def triage(self):
        """Reads from triaging, moves into either: ready or finished."""
        try:
            async with self._tsm.lock:
                task_info = self._tsm.triaging.pop()
        except IndexError:
            return

        requirements_ok = await self._spawner.spawn_task(task_info)
        if requirements_ok:
            async with self._tsm.lock:
                self._tsm.ready.append(task_info)
        else:
            async with self._tsm.lock:
                self._tsm.finished.append(task_info)
                task_info.status = 'FAILED ON TRIAGE'

    async def start(self):
        """Reads from ready, moves into either: started or finished."""
        try:
            async with self._tsm.lock:
                task_info = self._tsm.ready.pop()
        except IndexError:
            return

        # enforce a rate limit on the number of started (currently
        # running) tasks.  this is a global limit, but the spawners
        # can also be queried with regards to their capacity to handle
        # new tasks
        async with self._tsm.lock:
            if len(self._tsm.started) >= self._max_running:
                self._tsm.ready.insert(0, task_info)
                task_info.status = 'WAITING'
                return

        start_ok = await self._spawner.spawn_task(task_info)
        if start_ok:
            task_info.status = None
            if self._task_timeout is not None:
                task_info.execution_timeout = time.monotonic() + self._task_timeout
            async with self._tsm.lock:
                self._tsm.started.append(task_info)
        else:
            async with self._tsm.lock:
                self._tsm.finished.append(task_info)

    async def monitor(self):
        """Reads from started, moves into finished."""
        try:
            async with self._tsm.lock:
                task_info = self._tsm.started.pop()
        except IndexError:
            return

        if self._spawner.is_task_alive(task_info):
            try:
                if task_info.execution_timeout is None:
                    remaining = None
                else:
                    remaining = task_info.timeout - time.monotonic()
                await asyncio.wait_for(self._spawner.wait_task(task_info),
                                       remaining)
                task_info.status = 'FINISHED'
            except asyncio.TimeoutError:
                task_info.status = 'FINISHED W/ TIMEOUT'

        async with self._tsm.lock:
            self._tsm.finished.append(task_info)

    async def run(self):
        """Pushes Tasks forward and makes them do something with their lifes."""
        while True:
            is_complete = await self._tsm.complete
            if is_complete:
                break
            await self.bootstrap()
            await self.triage()
            await self.start()
            await self.monitor()
