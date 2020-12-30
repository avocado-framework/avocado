import asyncio
from unittest import TestCase

from avocado.core.nrunner import Runnable, Task
from avocado.core.status.repo import StatusRepo
from avocado.core.task import statemachine
from avocado.core.task.runtime import RuntimeTask
from avocado.plugins.spawners.process import ProcessSpawner as Spawner

# This test should, provided the environment supports, also be able
# to run successfully with other spawners, such as:
#
# from avocado.plugins.spawners.podman import PodmanSpawner as Spawner


class StateMachine(TestCase):

    def test(self):
        number_of_tasks = 80
        number_of_workers = 8

        runnable = Runnable("noop", "noop")
        runtime_tasks = [RuntimeTask(Task(runnable, "%03i" % _))
                         for _ in range(1, number_of_tasks + 1)]
        spawner = Spawner()
        status_repo = StatusRepo()

        state_machine = statemachine.TaskStateMachine(runtime_tasks, status_repo)
        loop = asyncio.get_event_loop()
        workers = [statemachine.Worker(state_machine, spawner).run()
                   for _ in range(number_of_workers)]

        loop.run_until_complete(asyncio.gather(*workers))
        self.assertEqual(number_of_tasks, len(state_machine.finished))
