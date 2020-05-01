import asyncio
from multiprocessing import cpu_count

from .spawners.process import ProcessSpawner


class SchedulerException(Exception):
    """Base exception for the Scheduller."""


class SchedulerNoPendingTasksException(SchedulerException):
    """Exception raised when there are no more pending tasks to be started."""


class Scheduler:
    """Manages the scheduling of tasks, keeping track of the their status."""

    #: The interval given to other coroutines when a the scheduler needs
    #: to wait, for instance, for the conclusion of all tasks
    INTERVAL = 0.05

    def __init__(self, tasks, parallel_tasks=None, spawner=None):
        """Initializes a new scheduler.

        :param tasks: the tasks to be scheduled to be executed
        :type tasks: list of :class:`avocado.core.nrunner.Task`
        :param parallel_tasks: the number of parallel tasks that will be kept
                               running at any given time.  It defaults to
                               twice the number of active CPUs in the local
                               system, minus one.
        :type parallel_tasks: int
        :param spawner: an instance of a spawner to be used in starting tasks
                        and checking for their "health", that is, if a task
                        appears to be alive or not.  It defaults to a
                       :class:`avocado.core.spawners.process.ProcessSpawner`
        :type spawner: :class:`avocado.core.spawners.common.BaseSpawner`
        """
        self.pending_tasks = tasks

        if parallel_tasks is None:
            parallel_tasks = 2 * cpu_count() - 1
        self.parallel_tasks = parallel_tasks

        if spawner is None:
            spawner = ProcessSpawner()
        self.spawner = spawner
        self.started_tasks = []
        self.start_failed_tasks = []
        #: Tasks that have finished from the manager perspective
        self.finished_tasks = []

    def __repr__(self):
        return ('<Scheduler pending: "{}" started: "{}" start failed: {} '
                'finished: "{}">').format(self.pending_tasks,
                                          self.started_tasks,
                                          self.start_failed_tasks,
                                          self.finished_tasks)

    @asyncio.coroutine
    def tick(self):
        """Runs one cycle of scheduler tasks, based on current parallel tasks.

        This method facilitates the use of the scheduler in a loop.  It will
        return False if new task was not spawned, which can be used to abort
        a loop.

        :rtype: bool
        """
        yield from self.reconcile_task_status()
        if self.is_complete():
            return False
        if not self.should_spawn_new_task():
            return False
        try:
            result = yield from self.spawn_next_task()
            return result
        except SchedulerNoPendingTasksException:
            return False

    def should_spawn_new_task(self):
        """Whether to spawn a new task based on the current load."""
        return len(self.started_tasks) < self.parallel_tasks

    @asyncio.coroutine
    def spawn_task(self, task):
        """Spawns a task with the scheduler spawner.

        If the task is found in the list of pending tasks, it's
        removed from that list.  This allows users of the scheduler to
        spawn tasks not originally in the list of pending tasks.
        """
        try:
            self.pending_tasks.remove(task)
        except ValueError:
            pass
        spawned_result = yield from self.spawner.spawn_task(task)
        if spawned_result:
            self.started_tasks.append(task)
            # REMOVEME
            print("Started task: %s" % task.identifier)
        else:
            self.start_failed_tasks.append(task)
            # REMOVEME
            print("Failed to start task: %s" % task.identifier)
        return spawned_result

    @asyncio.coroutine
    def spawn_next_task(self):
        """Spawns the next pending task.

        :raises: SchedulerNoPendingTasksException if there are no more pending
                 tasks
        """
        try:
            task = self.pending_tasks.pop(0)
        except IndexError:
            raise SchedulerNoPendingTasksException
        spawned_result = yield from self.spawn_task(task)
        return spawned_result

    def is_complete(self):
        """Returns whether there's any pending or not yet finished task.

        :rtype: bool
        """
        return not (self.pending_tasks or self.started_tasks)

    @asyncio.coroutine
    def wait_until_complete(self):
        """Waits until the scheduler is complete, reconciling often."""
        while True:
            if not self.is_complete():
                yield from self.reconcile()
            else:
                break

    @asyncio.coroutine
    def reconcile_task_status(self):
        """Reconcile the status of tasks, such as from started to finished.

        This happens after letting coroutings check on tasks status."""
        yield from asyncio.sleep(self.INTERVAL)
        finished_tasks = [task for task in self.started_tasks
                          if not self.spawner.is_task_alive(task)]
        for task in finished_tasks:
            self.started_tasks.remove(task)
            self.finished_tasks.append(task)
