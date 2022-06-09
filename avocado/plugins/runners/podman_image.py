import asyncio
import time
from multiprocessing import Process, SimpleQueue

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import RUNNER_RUN_STATUS_INTERVAL, BaseRunner
from avocado.core.utils import messages
from avocado.utils.podman import Podman, PodmanException


class PodmanImageRunner(BaseRunner):
    """Runner for dependencies of type podman-image

    This runner handles download and verification.

    Runnable attributes usage:

     * kind: 'podman-image'

     * uri: the name of the image

     * args: not used
    """

    name = 'podman-image'
    description = f'Runner for dependencies of type {name}'

    def _run_podman_pull(self, uri, queue):
        try:
            podman = Podman()
            loop = asyncio.get_event_loop()
            loop.run_until_complete(podman.execute('pull', uri))
            result = 'pass'
        except PodmanException:
            result = 'fail'
        queue.put({'result': result})

    def run(self, runnable):
        # pylint: disable=W0201
        self.runnable = runnable
        yield messages.StartedMessage.get()

        if not runnable.uri:
            reason = 'uri identifying the podman image is required'
            yield messages.FinishedMessage.get('error', reason)
        else:
            queue = SimpleQueue()
            process = Process(target=self._run_podman_pull,
                              args=(runnable.uri, queue))
            process.start()
            while queue.empty():
                time.sleep(RUNNER_RUN_STATUS_INTERVAL)
                yield messages.RunningMessage.get()

            output = queue.get()
            yield messages.FinishedMessage.get(output['result'])


class RunnerApp(BaseRunnerApp):
    PROG_NAME = f'avocado-runner-{PodmanImageRunner.name}'
    PROG_DESCRIPTION = (PodmanImageRunner.description)
    RUNNABLE_KINDS_CAPABLE = [PodmanImageRunner.name]


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == '__main__':
    main()
