import asyncio
import itertools
import random
import time

from avocado.utils.astring import tabular_output

DEBUG = False


def debug(msg):
    if DEBUG:
        print(msg)


async def sleep_random():
    await asyncio.sleep(random.random())


def true_or_false(handicap=3):
    """Returns a random positive or negative outcome, with some bias."""
    if handicap > 1:
        choices = [True] + ([False] * handicap)
    else:
        choices = [False] + ([True] * abs(handicap))
    return random.choice(choices)


def mock_check_task_requirement():
    # More success than failures, please
    return true_or_false(-8)


def mock_check_task_start():
    # More success than failures, please
    return true_or_false(-6)


def mock_monitor_task_finished():
    # More failures than successes, please
    return true_or_false(5)


class Task:
    """Used here as a placeholder for an avocado.core.nrunner.Task."""

    def __init__(self, identification):
        self._identification = identification


class TaskInfo(Task):
    """Task with extra status information on its life-cycle.

    The equivalent of a StatusServer will contain this information
    in the real implementation."""

    def __init__(self, identification):
        super(TaskInfo, self).__init__(identification)
        self._status = None
        self._timeout = None

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        self._timeout = timeout

    def __repr__(self):
        if self._status is None:
            return '%s' % self._identification
        else:
            return '%s (%s)' % (self._identification,
                                self.status)


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

    def __str__(self):
        headers = ("|_REQUESTED_|", "|_TRIAGING__|",
                   "|___READY___|", "|__STARTED__|",
                   "|______FINISHED_______|")
        data = itertools.zip_longest(self._requested, self._triaging, self._ready,
                                     self._started, self._finished, fillvalue="")
        matrix = [_ for _ in data]
        return tabular_output(matrix, headers)


async def bootstrap(lc):
    """Reads from requested, moves into triaging."""
    # fake some rate limiting
    if true_or_false(10):
        return
    try:
        async with lc.lock:
            task = lc.requested.pop()
            lc.triaging.append(task)
            debug('Moved Task %s: REQUESTED => TRIAGING' % task)
    except IndexError:
        debug('BOOTSTRAP: nothing to do')
        return


async def triage(lc):
    """Reads from triaging, moves into either: ready or finished."""
    await sleep_random()
    try:
        async with lc.lock:
            task = lc.triaging.pop()
    except IndexError:
        debug('TRIAGE done')
        return

    if mock_check_task_requirement():
        async with lc.lock:
            lc.ready.append(task)
            debug('Moving Task %s: TRIAGING => READY' % task)
    else:
        async with lc.lock:
            lc.finished.append(task)
            task.status = 'FAILED ON TRIAGE'
            debug('Moving Task %s: TRIAGING => FINISHED' % task)


async def start(lc):
    """Reads from ready, moves into either: started or finished."""
    await sleep_random()
    try:
        async with lc.lock:
            task = lc.ready.pop()
    except IndexError:
        debug('START: nothing to do')
        return

    # enforce a rate limit on the number of started (currently running) tasks.
    # this is a global limit, but the spawners can also be queried with regards
    # to their capacity to handle new tasks
    MAX_RUNNING_TASKS = 8
    async with lc.lock:
        if len(lc.started) >= MAX_RUNNING_TASKS:
            lc.ready.insert(0, task)
            task.status = 'WAITING'
            return

    # suppose we're starting the tasks
    if mock_check_task_start():
        async with lc.lock:
            task.status = None
            # Let's give each task 15 seconds from start time
            task.timeout = time.monotonic() + 15
            lc.started.append(task)
            debug('Moving Task %s: READY => STARTED' % task)
    else:
        async with lc.lock:
            lc.finished.append(task)
            task.status = 'FAILED ON START'
            debug('Moving Task %s: READY => FINISHED (ERRORED ON START)' % task)


async def monitor(lc):
    """Reads from started, moves into finished."""
    await sleep_random()
    try:
        async with lc.lock:
            task = lc.started.pop()
    except IndexError:
        debug('MONITOR: nothing to do')
        return

    if time.monotonic() > task.timeout:
        async with lc.lock:
            task.status = 'FAILED W/ TIMEOUT'
            lc.finished.append(task)
            debug('Moving Task %s: STARTED => FINISHED (FAILED ON TIMEOUT)' % task)
    elif mock_monitor_task_finished():
        async with lc.lock:
            lc.finished.append(task)
            debug('Moving Task %s: STARTED => FINISHED (COMPLETED AFTER STARTED)' % task)
    else:
        async with lc.lock:
            lc.started.insert(0, task)
        debug('Task %s: has not finished yet' % task)


def print_lc_status(lc):
    print("\033c", end="")
    print(str(lc))


async def worker(lc):
    """Pushes Tasks forward and makes them do something with their lives."""
    while True:
        complete = await lc.complete
        debug('Complete? %s' % complete)
        if complete:
            break
        await bootstrap(lc)
        print_lc_status(lc)
        await triage(lc)
        print_lc_status(lc)
        await start(lc)
        print_lc_status(lc)
        await monitor(lc)
        print_lc_status(lc)


if __name__ == '__main__':
    NUMBER_OF_TASKS = 40
    NUMBER_OF_LIFECYCLE_WORKERS = 4
    tasks_info = [TaskInfo("%03i" % _) for _ in range(1, NUMBER_OF_TASKS - 1)]
    state_machine = TaskStateMachine(tasks_info)
    loop = asyncio.get_event_loop()
    workers = [loop.create_task(worker(state_machine))
               for _ in range(NUMBER_OF_LIFECYCLE_WORKERS)]
    loop.run_until_complete(asyncio.gather(*workers))
    print("JOB COMPLETED")
