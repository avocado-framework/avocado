import asyncio
import logging
import sys
import time
from multiprocessing import Process, SimpleQueue, set_start_method

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

    name = "podman-image"
    description = f"Runner for dependencies of type {name}"

    def _run_podman_pull(self, uri, queue):
        # Silence the podman utility from outputting messages into
        # the regular handler, which will go to stdout.  The
        # exceptions caught here still contain all the needed
        # information for debugging in case of errors.
        logging.getLogger("avocado.utils.podman").addHandler(logging.NullHandler())
        try:
            podman = Podman()
            loop = asyncio.get_event_loop()
            loop.run_until_complete(podman.execute("pull", uri))
            queue.put({"result": "pass"})
        except PodmanException as ex:
            queue.put(
                {"result": "fail", "fail_reason": f"Could not pull podman image: {ex}"}
            )

    def run(self, runnable):
        yield messages.StartedMessage.get()

        if not runnable.uri:
            reason = "uri identifying the podman image is required"
            yield messages.FinishedMessage.get("error", reason)
        else:
            queue = SimpleQueue()
            process = Process(target=self._run_podman_pull, args=(runnable.uri, queue))
            process.start()
            while queue.empty():
                time.sleep(RUNNER_RUN_STATUS_INTERVAL)
                yield messages.RunningMessage.get()

            output = queue.get()
            result = output.pop("result")
            yield messages.FinishedMessage.get(result, **output)


class RunnerApp(BaseRunnerApp):
    PROG_NAME = f"avocado-runner-{PodmanImageRunner.name}"
    PROG_DESCRIPTION = PodmanImageRunner.description
    RUNNABLE_KINDS_CAPABLE = [PodmanImageRunner.name]


def main():
    if sys.platform == "darwin":
        set_start_method("fork")
    app = RunnerApp(print)
    app.run()


if __name__ == "__main__":
    main()
